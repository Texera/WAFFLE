package org.apache.texera.profile
import java.nio.file.{Files,Paths,StandardOpenOption}
import java.util.concurrent.ConcurrentHashMap
object Phase {
  private val path=Paths.get(sys.env("WAFFLE_PHASE_DIR"),"jvm.tsv")
  private val starts=new ConcurrentHashMap[String,java.lang.Long]()
  @volatile private var sample = -1
  private val base=java.time.Instant.now()
  private val mono=System.nanoTime()
  private def now: Long = base.getEpochSecond*1000000000L + base.getNano + (System.nanoTime()-mono)
  private def emit(kind:String,id:String,lo:Long,hi:Long):Unit=synchronized {
    Files.writeString(path,s"$sample\t$kind\t$id\t$lo\t$hi\n",StandardOpenOption.CREATE,StandardOpenOption.APPEND)
  }
  def beginSample(i:Int):Unit={sample=i;val v=now;emit("begin","-",v,v)}
  def endSample(i:Int):Unit={require(i==sample);val v=now;emit("end","-",v,v)}
  def launch(id:String):Unit={require(starts.putIfAbsent(id,now)==null,id)}
  def ready(id:String):Unit={val hi=now;val lo=starts.remove(id);require(lo!=null,id);emit("startup",id,lo,hi)}
  def timed[T](kind:String,id:String)(f: =>T):T={val lo=now;try f finally {val hi=now;emit(kind,id,lo,hi)}}
}
