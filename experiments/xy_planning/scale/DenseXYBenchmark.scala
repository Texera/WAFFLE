/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

package org.apache.texera.amber.engine.architecture.scheduling

import java.nio.charset.StandardCharsets.UTF_8
import java.nio.file.{Files, Paths}
import java.util.concurrent.{Callable, FutureTask, TimeUnit, TimeoutException}

/** One separately capped search on a balanced branching graph. */
object DenseXYBenchmark {
  def main(args: Array[String]): Unit = {
    require(args.length == 2 || args.length == 3)
    val groups = if (args.length == 3) args(2).toInt else 12
    require(groups >= 6 && groups <= 12)
    val folder = Paths.get(args(0))
    val method = args(1)
    require(Set("X", "Y").contains(method))
    Files.createDirectories(folder)
    def search(input: XYPlanningComparison.Input): XYPlanningComparison.Result =
      if (method == "X") XYPlanningComparison.searchX(input, pruning = true)
      else XYPlanningComparison.searchY(input, pruning = true)
    val warmup = NativeBranchXYFixtures.compileScale(4, 4, 0).input
    for (_ <- 1 to 3) require(search(warmup).cost == 19)
    val compiled = NativeBranchXYFixtures.compileScale(groups, groups, 0)
    val input = compiled.input
    require(input.plan.operators.size == 4 + 8 * groups && compiled.original.getBlockingAndDependeeLinks.size == 4 * groups)
    val edges = input.plan.links.toVector.sortBy(_.toString)
    val required = input.plan.getBlockingAndDependeeLinks
    val names = CompiledXYBenchmark.operatorKey _
    val nodesText = input.plan.operators.toVector.sortBy(op => names(op.id)).map { op =>
      Seq(names(op.id), input.weights(op.id), input.block(op.id)).mkString(",")
    }
    val edgesText = edges.map(e => Seq(names(e.fromOpId), names(e.toOpId), required(e)).mkString(","))
    Files.writeString(folder.resolve("operators.csv"), ("operator,estimate,inside" +: nodesText).mkString("", "\n", "\n"), UTF_8)
    Files.writeString(folder.resolve("edges.csv"), ("from,to,required" +: edgesText).mkString("", "\n", "\n"), UTF_8)
    val task = new FutureTask(new Callable[XYPlanningComparison.Result] {
      def call(): XYPlanningComparison.Result = search(input)
    })
    val worker = new Thread(task)
    worker.setDaemon(true)
    val limit = 120
    val start = System.nanoTime()
    worker.start()
    val row = try {
      val result = task.get(limit, TimeUnit.SECONDS)
      val elapsed = System.nanoTime() - start
      require(XYPlanningComparison.evaluate(input, result.materialized).contains(result.cost))
      val indices = edges.indices.filter(i => result.materialized(edges(i))).mkString(";")
      Seq(method,"completed",limit,elapsed,result.totalNs,result.states,result.cost,indices).mkString(",")
    } catch {
      case _: TimeoutException =>
        Seq(method,"timeout",limit,System.nanoTime() - start,"","","","").mkString(",")
    }
    Files.writeString(folder.resolve("outcome.csv"), "method,status,limit_s,wall_ns,total_ns,states,cost,cuts\n" + row + "\n", UTF_8)
    println(s"Dense planning trial: $row")
  }
}
