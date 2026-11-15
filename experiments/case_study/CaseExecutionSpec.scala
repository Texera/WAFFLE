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
import org.apache.texera.common.config.ApplicationConfig
import org.apache.texera.amber.tags.IntegrationTest
import org.scalatest.flatspec.AnyFlatSpecLike
import org.scalatest.BeforeAndAfterAll
import java.nio.file.{Files, Paths, StandardOpenOption}
import scala.jdk.CollectionConverters._

@IntegrationTest
class CaseExecutionSpec extends TestKit(ActorSystem("CaseExecutionSpec", AmberRuntime.pekkoConfig))
    with AnyFlatSpecLike with BeforeAndAfterAll {
  private val root = Paths.get(sys.env("WAFFLE_EXPERIMENT_PACKAGE"))
  private val runs = objectMapper.readTree(root.resolve("manifest.json").toFile).get("runs").elements().asScala.toList
  private val executionBase = 100000000 + scala.util.Random.nextInt(1000000000)
  override def beforeAll(): Unit = {
    require(ApplicationConfig.maxConcurrentRegions == 1)
    system.actorOf(Props[SingleNodeListener](), "cluster-info")
    initiateTexeraDBForTestCases()
  }
  override def afterAll(): Unit = TestKit.shutdownActorSystem(system)
  runs.zipWithIndex.foreach { case (run, index) =>
    "KNIME translation" should s"run sample $index ${run.get("case").asText} ${run.get("strategy").asText}" in {
      val graph = objectMapper.readTree(root.resolve(run.get("workflow").asText).toFile)
      val ops = graph.get("operators").elements().asScala.map { node =>
        val flat = node.get("operatorProperties").deepCopy[com.fasterxml.jackson.databind.node.ObjectNode]()
        List("operatorID", "operatorType", "inputPorts", "outputPorts").foreach(k => flat.set[com.fasterxml.jackson.databind.JsonNode](k,node.get(k)))
        objectMapper.treeToValue(flat,classOf[LogicalOp])
      }.toList
      val byName=ops.map(o=>o.operatorIdentifier.id -> o).toMap
      val links=graph.get("links").elements().asScala.map(e=>LogicalLink(
        byName(e.get("source").get("operatorID").asText).operatorIdentifier,PortIdentity(),
        byName(e.get("target").get("operatorID").asText).operatorIdentifier,PortIdentity())).toList
      val id=executionBase+index
      setUpWorkflowExecutionData(id)
      try {
        val context=workflowContext(id,WorkflowSettings(dataTransferBatchSize=400,executionMode=ExecutionMode.MATERIALIZED))
        val compileStart=System.nanoTime()
        val workflow=buildWorkflow(ops,links,context)
        val compileNs=System.nanoTime()-compileStart
        val started=System.nanoTime()
        val result=runWorkflowAndReadResults(system,workflow,List(ops.last.operatorIdentifier),_.get().toList,Duration.fromSeconds(600))(ops.last.operatorIdentifier)
        val elapsed=System.nanoTime()-started
        val fields=run.get("fields").elements().asScala.map(_.asText).toList
        val rows=result.map(r=>fields.map(n=>n -> r.getField[Any](n)).toMap)
        val record=Map[String,Any]("sample"->index,"case"->run.get("case").asText,"strategy"->run.get("strategy").asText,
          "pair"->run.get("pair").asInt,"warmup"->run.get("warmup").asBoolean,"execution_ns"->elapsed,
          "compilation_ns"->compileNs,"execution_id"->id,"rows"->rows)
        Files.writeString(root.resolve("native.jsonl"),objectMapper.writeValueAsString(record)+"\n",StandardOpenOption.CREATE,StandardOpenOption.APPEND)
        assert(rows.nonEmpty, "translation produced no rows")
        println(s"MEASURED sample=$index case=${run.get("case").asText} strategy=${run.get("strategy").asText} seconds=${elapsed/1e9}")
      } finally cleanupWorkflowExecutionData(id)
    }
  }
}
