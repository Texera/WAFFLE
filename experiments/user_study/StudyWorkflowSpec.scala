// External research harness. Add through sbt's unmanagedSources setting.
// No Texera source or build file needs to be changed.
package org.apache.texera.amber.engine.e2e

import com.twitter.util.Duration
import org.apache.pekko.actor.{ActorSystem, Props}
import org.apache.pekko.testkit.TestKit
import org.apache.texera.amber.clustering.SingleNodeListener
import org.apache.texera.amber.engine.common.AmberRuntime
import org.apache.texera.amber.engine.e2e.TestUtils._
import org.apache.texera.amber.core.workflow.{ExecutionMode, PortIdentity, WorkflowSettings}
import org.apache.texera.amber.operator.LogicalOp
import org.apache.texera.amber.util.JSONUtils.objectMapper
import org.apache.texera.common.compiler.model.LogicalLink
import org.apache.texera.amber.tags.IntegrationTest
import org.scalatest.flatspec.AnyFlatSpecLike
import org.scalatest.BeforeAndAfterAll
import java.nio.file.{Files, Paths}
import scala.jdk.CollectionConverters._

@IntegrationTest
class StudyWorkflowSpec
    extends TestKit(ActorSystem("StudyWorkflowSpec", AmberRuntime.pekkoConfig))
    with AnyFlatSpecLike with BeforeAndAfterAll {
  private val root = Paths.get(sys.env("WAFFLE_STUDY_PACKAGE"))
  private val manifest = objectMapper.readTree(root.resolve("manifest.json").toFile)
  private val runs = manifest.get("runs").elements().asScala.filter(_.get("tool").asText == "waffle").toList
  // The Iceberg catalog survives a JVM run; never reuse an execution's append table.
  private val executionBase = 100000000 + scala.util.Random.nextInt(1000000000)

  override def beforeAll(): Unit = {
    system.actorOf(Props[SingleNodeListener](), "cluster-info")
    initiateTexeraDBForTestCases()
  }
  override def afterAll(): Unit = TestKit.shutdownActorSystem(system)

  runs.zipWithIndex.foreach { case (run, index) =>
    val label = run.get("id").asText
    "WAFFLE native engine" should s"execute $label and preserve the expected result rows" in {
      val path = root.resolve(run.get("workflow").asText)
      val dir = path.getParent
      Files.deleteIfExists(dir.resolve("visits.csv"))
      Files.deleteIfExists(dir.resolve("results.csv"))
      Files.deleteIfExists(dir.resolve("engine-result.txt"))
      Files.deleteIfExists(dir.resolve("exit-code.txt"))
      val graph = objectMapper.readTree(path.toFile)
      val ops = graph.get("operators").elements().asScala.map { node =>
        val flattened = node.get("operatorProperties").deepCopy[com.fasterxml.jackson.databind.node.ObjectNode]()
        List("operatorID", "operatorType", "inputPorts", "outputPorts").foreach { key =>
          flattened.set[com.fasterxml.jackson.databind.JsonNode](key, node.get(key))
        }
        objectMapper.treeToValue(flattened, classOf[LogicalOp])
      }.toList
      val byName = ops.map(o => o.operatorIdentifier.id -> o).toMap
      val links = graph.get("links").elements().asScala.map { edge =>
        LogicalLink(byName(edge.get("source").get("operatorID").asText).operatorIdentifier,
          PortIdentity(), byName(edge.get("target").get("operatorID").asText).operatorIdentifier, PortIdentity())
      }.toList
      val id = executionBase + index
      setUpWorkflowExecutionData(id)
      try {
        val context = workflowContext(id, WorkflowSettings(dataTransferBatchSize = 400, executionMode = ExecutionMode.MATERIALIZED))
        val rows = runWorkflowAndReadResults(system, buildWorkflow(ops, links, context),
          List(ops.last.operatorIdentifier), _.get().toList, Duration.fromSeconds(180))(ops.last.operatorIdentifier)
        val isFiles = run.get("task").asText.startsWith("files")
        val expected = run.get("expected").elements().asScala.map(x =>
          (x.get(if (isFiles) "filename" else "K").asText,
            x.get(if (isFiles) "mean" else "score").asDouble)).toList
        val actual = rows.map(r =>
          (if (isFiles) r.getField[String]("filename") else r.getField[Int]("K").toString,
            r.getField[Double](if (isFiles) "mean" else "score")))
        assert(actual.size == expected.size, s"$label: $actual != $expected")
        actual.zip(expected).foreach { case ((a, x), (b, y)) =>
          assert(a == b && math.abs(x-y) <= 1e-9 * math.max(1.0, math.abs(y)),
            s"$label: $actual != $expected")
        }
        Files.writeString(dir.resolve("engine-result.txt"), s"PASS native materialized results: $actual\n")
        Files.writeString(dir.resolve("exit-code.txt"), "0\n")
      } finally {
        cleanupWorkflowExecutionData(id)
      }
    }
  }
}
