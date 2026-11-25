package org.apache.texera.amber.engine.e2e

import com.twitter.util.{Await, Duration, Promise, Return, Throw}
import org.apache.pekko.actor.{ActorSystem, Props}
import org.apache.pekko.testkit.TestKit
import org.apache.texera.amber.clustering.SingleNodeListener
import org.apache.texera.amber.core.workflow.{ExecutionMode, PortIdentity, WorkflowSettings}
import org.apache.texera.amber.engine.architecture.coordinator.{CoordinatorConfig, ExecutionStateUpdate, FatalError}
import org.apache.texera.amber.engine.architecture.rpc.controlcommands.{ConsoleMessage, ConsoleMessageType, EmptyRequest}
import org.apache.texera.amber.engine.architecture.rpc.controlreturns.WorkflowAggregatedState.COMPLETED
import org.apache.texera.amber.engine.common.AmberRuntime
import org.apache.texera.amber.engine.common.client.AmberClient
import org.apache.texera.amber.engine.e2e.TestUtils._
import org.apache.texera.amber.operator.LogicalOp
import org.apache.texera.amber.util.JSONUtils.objectMapper
import org.apache.texera.common.compiler.model.LogicalLink
import org.scalatest.BeforeAndAfterAll
import org.scalatest.flatspec.AnyFlatSpecLike
import java.nio.file.{Files, Paths, StandardOpenOption}
import scala.jdk.CollectionConverters._

class ScopedMergeSpec extends TestKit(ActorSystem("ScopedMergeSpec", AmberRuntime.pekkoConfig))
    with AnyFlatSpecLike with BeforeAndAfterAll {
  private val root = Paths.get(sys.env("WAFFLE_EXPERIMENT_PACKAGE"))
  private val runs = objectMapper.readTree(root.resolve("manifest.json").toFile).get("runs").elements().asScala.toList
  private val executionBase = 100000000 + scala.util.Random.nextInt(1000000000)
  override def beforeAll(): Unit = {
    system.actorOf(Props[SingleNodeListener](), "cluster-info")
    initiateTexeraDBForTestCases()
  }
  override def afterAll(): Unit = TestKit.shutdownActorSystem(system)

  runs.zipWithIndex.foreach { case (run, index) =>
    val scenario = run.get("case").asText
    val layout = run.get("layout").asText
    "A two-branch loop" should s"evaluate $scenario with layout $layout" in {
      val graph = objectMapper.readTree(root.resolve(run.get("workflow").asText).toFile)
      val ops = graph.get("operators").elements().asScala.map { node =>
        val flat = node.get("operatorProperties").deepCopy[com.fasterxml.jackson.databind.node.ObjectNode]()
        List("operatorID", "operatorType", "inputPorts", "outputPorts").foreach { key =>
          flat.set[com.fasterxml.jackson.databind.JsonNode](key, node.get(key))
        }
        objectMapper.treeToValue(flat, classOf[LogicalOp])
      }.toList
      val byName = ops.map(o => o.operatorIdentifier.id -> o).toMap
      val links = graph.get("links").elements().asScala.map { e =>
        LogicalLink(byName(e.get("source").get("operatorID").asText).operatorIdentifier, PortIdentity(),
                    byName(e.get("target").get("operatorID").asText).operatorIdentifier, PortIdentity())
      }.toList
      val id = executionBase + index
      setUpWorkflowExecutionData(id)
      try {
        val workflow = buildWorkflow(ops, links, workflowContext(id, WorkflowSettings(
          dataTransferBatchSize = 400, executionMode = ExecutionMode.MATERIALIZED)))
        val terminal = Promise[Option[ConsoleMessage]]()
        val client = new AmberClient(system, workflow.context, workflow.physicalPlan, CoordinatorConfig.default,
          e => terminal.updateIfEmpty(Throw(e)))
        try {
          registerResultUriPersistence(client, workflow.context.executionId)
          client.registerCallback[FatalError](evt => terminal.updateIfEmpty(Throw(evt.e)))
          client.registerCallback[ConsoleMessage](m => {
            if (m.msgType == ConsoleMessageType.ERROR) terminal.updateIfEmpty(Return(Some(m)))
          })
          client.registerCallback[ExecutionStateUpdate](e => {
            if (e.state == COMPLETED) terminal.updateIfEmpty(Return(None))
          })
          Await.result(client.coordinatorInterface.startWorkflow(EmptyRequest(), ()))
          val error = Await.result(terminal, Duration.fromSeconds(240))
          val evidence: Map[String, Any] = error match {
            case Some(msg) =>
              val text = msg.title + " " + msg.message
              val detail = """Binding conflict for K in [^:\s]+: [23] versus [23]""".r.findFirstIn(text)
              assert(scenario == "conflict" && msg.workerId.contains("merge") && detail.isDefined, text)
              Map("outcome" -> "conflict", "worker" -> msg.workerId, "error" -> detail.get)
            case None =>
              assert(scenario != "conflict", "conflicting bindings reached completion")
              val rows = readMaterializedResults(workflow)(ops.last.operatorIdentifier)
              val fields = run.get("fields").elements().asScala.map(_.asText).toList
              val values = rows.map(row => fields.map(k => k -> row.getField[Any](k)).toMap)
              val expectedK = if (scenario == "new-iteration") List(2, 3) else List(2)
              assert(values.map(_("K").asInstanceOf[Number].intValue).sorted == expectedK)
              values.foreach { row =>
                assert(row("rows_seen") == 2)
                assert(row("ratio") == (if (scenario == "independent") 0.8 else 0.0))
                assert(row("calls") == (if (scenario == "independent") 2 else 1))
              }
              Map("outcome" -> "completed", "rows" -> values)
          }
          val record = evidence ++ Map("case" -> scenario, "layout" -> layout, "execution_id" -> id)
          Files.writeString(root.resolve("native.jsonl"), objectMapper.writeValueAsString(record) + "\n",
            StandardOpenOption.CREATE, StandardOpenOption.APPEND)
        } finally client.shutdown()
      } finally cleanupWorkflowExecutionData(id)
    }
  }
}
