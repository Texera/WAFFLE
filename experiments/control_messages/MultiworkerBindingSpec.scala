package org.apache.texera.amber.engine.e2e

import com.twitter.util.Duration
import org.apache.pekko.actor.{ActorSystem, Props}
import org.apache.pekko.testkit.TestKit
import org.apache.texera.amber.clustering.SingleNodeListener
import org.apache.texera.amber.core.executor.OpExecWithClassName
import org.apache.texera.amber.core.tuple.{Tuple, TupleLike}
import org.apache.texera.amber.core.workflow.{ExecutionMode, PortIdentity, WorkflowSettings}
import org.apache.texera.amber.engine.common.AmberRuntime
import org.apache.texera.amber.engine.e2e.TestUtils._
import org.apache.texera.amber.operator.LogicalOp
import org.apache.texera.amber.operator.filter.{SpecializedFilterOpDesc, SpecializedFilterOpExec}
import org.apache.texera.amber.tags.IntegrationTest
import org.apache.texera.amber.util.JSONUtils.objectMapper
import org.apache.texera.common.compiler.model.LogicalLink
import org.apache.texera.common.config.ApplicationConfig
import org.scalatest.BeforeAndAfterAll
import org.scalatest.flatspec.AnyFlatSpecLike

import java.nio.file.{Files, Paths, StandardOpenOption}
import java.util.concurrent.ConcurrentLinkedQueue
import scala.jdk.CollectionConverters._

// All workers run on this test JVM. Each executor contributes a separate observation.
// Reading the inherited descriptor leaves compilation, binding and filtering unchanged.
object BindingObservations {
  val firstTuples = new ConcurrentLinkedQueue[Map[String, Int]]()
}

class ObservedFilter(descString: String, workerIndex: Int, workerCount: Int)
    extends SpecializedFilterOpExec(descString) {
  private var first = true

  override def processTuple(tuple: Tuple, port: Int): Iterator[TupleLike] = {
    if (first) {
      val field = classOf[SpecializedFilterOpExec].getDeclaredField("desc")
      field.setAccessible(true)
      val setting = field.get(this).asInstanceOf[SpecializedFilterOpDesc]
      BindingObservations.firstTuples.add(Map(
        "worker" -> workerIndex,
        "workers" -> workerCount,
        "bound_K" -> setting.predicates.head.value.toInt,
        "received_K" -> state.get.values("K").asInstanceOf[Number].intValue(),
        "first_x" -> tuple.getField[Number]("x").intValue()
      ))
      first = false
    }
    super.processTuple(tuple, port)
  }
}

@IntegrationTest
class MultiworkerBindingSpec
    extends TestKit(ActorSystem("MultiworkerBindingSpec", AmberRuntime.pekkoConfig))
    with AnyFlatSpecLike with BeforeAndAfterAll {
  private val root = Paths.get(sys.env("WAFFLE_EXPERIMENT_PACKAGE"))
  private val manifest = objectMapper.readTree(root.resolve("manifest.json").toFile)
  private val runs = manifest.get("runs").elements().asScala.toList
  private val rowCount = manifest.get("rows").asInt
  private val executionBase = 100000000 + scala.util.Random.nextInt(1000000000)

  override def beforeAll(): Unit = {
    require(ApplicationConfig.maxConcurrentRegions == 1)
    system.actorOf(Props[SingleNodeListener](), "cluster-info")
    initiateTexeraDBForTestCases()
  }
  override def afterAll(): Unit = TestKit.shutdownActorSystem(system)

  runs.zipWithIndex.foreach { case (run, index) =>
    val count = run.get("workers").asInt
    val repetition = run.get("repeat").asInt
    "Multiworker binding" should s"run workers=$count repeat=$repetition" in {
      BindingObservations.firstTuples.clear()
      val graph = objectMapper.readTree(root.resolve("workflow.json").toFile)
      val ops = graph.get("operators").elements().asScala.map { node =>
        val properties = node.get("operatorProperties").deepCopy[com.fasterxml.jackson.databind.node.ObjectNode]()
        List("operatorID", "operatorType", "inputPorts", "outputPorts").foreach { key =>
          properties.set[com.fasterxml.jackson.databind.JsonNode](key, node.get(key))
        }
        objectMapper.treeToValue(properties, classOf[LogicalOp])
      }.toList
      val byName = ops.map(op => op.operatorIdentifier.id -> op).toMap
      val links = graph.get("links").elements().asScala.map { link =>
        LogicalLink(
          byName(link.get("source").get("operatorID").asText).operatorIdentifier, PortIdentity(),
          byName(link.get("target").get("operatorID").asText).operatorIdentifier, PortIdentity()
        )
      }.toList
      val executionId = executionBase + index
      setUpWorkflowExecutionData(executionId)
      try {
        val context = workflowContext(executionId,
          WorkflowSettings(dataTransferBatchSize = 400, executionMode = ExecutionMode.MATERIALIZED))
        val compiled = buildWorkflow(ops, links, context)
        val filter = compiled.physicalPlan.operators.filter(_.id.logicalOpId.id == "binding-filter")
        assert(filter.size == 1)
        val original = filter.head
        val init = original.opExecInitInfo.asInstanceOf[OpExecWithClassName]
        val desc = objectMapper.readTree(init.descString)
        assert(desc.get("stateReferences").get("/predicates/0/value").asText == "K")
        val observed = original.copy(
          opExecInitInfo = OpExecWithClassName(classOf[ObservedFilter].getName, init.descString),
          suggestedWorkerNum = Some(count)
        )
        val plan = compiled.physicalPlan.copy(operators =
          compiled.physicalPlan.operators - original + observed)
        val workflow = compiled.copy(physicalPlan = plan)
        val result = runWorkflowAndReadResults(system, workflow,
          List(ops.last.operatorIdentifier), _.get().toList, Duration.fromSeconds(600)
        )(ops.last.operatorIdentifier)
        val rows = result.map { row =>
          List(row.getField[Number]("K").intValue(), row.getField[Number]("x").intValue())
        }.sortBy(row => (row.head, row(1)))
        val observations = BindingObservations.firstTuples.iterator().asScala.toList
          .sortBy(row => (row("received_K"), row("worker")))
        val record = Map[String, Any](
          "workers" -> count, "repeat" -> repetition, "input_rows" -> rowCount,
          "execution_id" -> executionId, "first_tuples" -> observations, "rows" -> rows
        )
        Files.writeString(root.resolve("native.jsonl"), objectMapper.writeValueAsString(record) + "\n",
          StandardOpenOption.CREATE, StandardOpenOption.APPEND)

        assert(observations.size == 2 * count, s"Missing first-tuple observation: $observations")
        for (k <- List(2, 3)) {
          val iteration = observations.filter(_("received_K") == k)
          assert(iteration.map(_("worker")).sorted == (0 until count).toList)
          assert(iteration.forall(row => row("bound_K") == k && row("workers") == count))
        }
        assert(rows == (for (k <- List(2, 3); x <- k until rowCount) yield List(k, x)))
        println(s"BINDING workers=$count repeat=$repetition observations=${observations.size} outputs=${rows.size}")
      } finally {
        cleanupWorkflowExecutionData(executionId)
      }
    }
  }
}
