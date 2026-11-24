package org.apache.texera.amber.engine.e2e

import java.nio.file.{Files, Paths, StandardOpenOption}
import java.security.MessageDigest
import scala.jdk.CollectionConverters._
import com.twitter.util.Duration
import org.apache.pekko.actor.{ActorSystem, Props}
import org.apache.pekko.testkit.TestKit
import org.apache.texera.amber.clustering.SingleNodeListener
import org.apache.texera.amber.core.workflow.{ExecutionMode, PortIdentity, WorkflowSettings}
import org.apache.texera.amber.engine.common.AmberRuntime
import org.apache.texera.amber.engine.e2e.TestUtils._
import org.apache.texera.amber.operator.LogicalOp
import org.apache.texera.amber.util.JSONUtils.objectMapper
import org.apache.texera.common.compiler.model.LogicalLink
import org.scalatest.BeforeAndAfterAll
import org.scalatest.flatspec.AnyFlatSpecLike

class GeneratedLoopSpec extends TestKit(ActorSystem("GeneratedLoopSpec", AmberRuntime.pekkoConfig))
    with AnyFlatSpecLike with BeforeAndAfterAll {
  private val root = Paths.get(sys.env("WAFFLE_GENERATED_RUN"))
  private val base = 100000000 + scala.util.Random.nextInt(1000000000)
  private val settings = WorkflowSettings(dataTransferBatchSize = 400, executionMode = ExecutionMode.MATERIALIZED)

  override def beforeAll(): Unit = {
    system.actorOf(Props[SingleNodeListener](), "cluster-info")
    initiateTexeraDBForTestCases()
  }
  override def afterAll(): Unit = TestKit.shutdownActorSystem(system)

  private def record(name: String, fields: Map[String, Any]): Unit =
    Files.writeString(root.resolve(name), objectMapper.writeValueAsString(fields) + "\n",
      StandardOpenOption.CREATE, StandardOpenOption.APPEND)

  private def compileGraph(index: Int, id: Int) = {
    val bytes = Files.readAllBytes(root.resolve(f"$index%03d.json"))
    val sha = MessageDigest.getInstance("SHA-256").digest(bytes).map(b => f"$b%02x").mkString
    val graph = objectMapper.readTree(bytes)
    val ops = graph.get("operators").elements().asScala.map { node =>
      val props = node.get("operatorProperties").deepCopy[com.fasterxml.jackson.databind.node.ObjectNode]()
      List("operatorID", "operatorType", "inputPorts", "outputPorts").foreach { k =>
        props.set[com.fasterxml.jackson.databind.JsonNode](k, node.get(k))
      }
      objectMapper.treeToValue(props, classOf[LogicalOp])
    }.toList
    val named = ops.map(o => o.operatorIdentifier.id -> o.operatorIdentifier).toMap
    val links = graph.get("links").elements().asScala.map { e =>
      require(e.at("/source/portID").asText == "output-0" && e.at("/target/portID").asText == "input-0")
      LogicalLink(named(e.at("/source/operatorID").asText), PortIdentity(),
        named(e.at("/target/operatorID").asText), PortIdentity())
    }.toList
    (buildWorkflow(ops, links, workflowContext(id, settings)), ops.last.operatorIdentifier, sha)
  }

  "WAFFLE strict compiler" should "build a physical workflow for each generated graph" in {
    (0 until 2000).foreach { i =>
      val (_, _, sha) = compileGraph(i, base + i)
      record("compiled.jsonl", Map("index" -> i, "graph_sha256" -> sha))
    }
  }

  // First of each family, plus a depth-three aggregation with two nonempty
  // transform arms at its final union, and the first four-stage graph.
  for (i <- List(0, 1, 2, 59, 399)) {
    "WAFFLE coordinator" should s"execute sentinel $i and read its materialized sink" in {
      val id = base + 2000 + i
      setUpWorkflowExecutionData(id)
      try {
        val (workflow, sink, sha) = compileGraph(i, id)
        val timeout = Duration.fromSeconds(if (i >= 59) 300 else 120)
        val tuples = runWorkflowAndReadResults(system, workflow, List(sink), _.get().toList, timeout)(sink)
        val rows = tuples.map(t => List(t.getField[Int]("step"), t.getField[Int]("score")))
        record("executed.jsonl", Map("index" -> i, "graph_sha256" -> sha, "rows" -> rows))
      } finally cleanupWorkflowExecutionData(id)
    }
  }
}
