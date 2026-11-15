import java.nio.file.*;
import java.sql.*;
import org.jooq.codegen.GenerationTool;
import org.jooq.meta.jaxb.*;
import org.apache.texera.dao.MockTexeraDB$;

/** Generate DAO classes from this checkout's DDL in a disposable database. */
public class GenerateSchema {
    public static void main(String[] args) throws Exception {
        var db = MockTexeraDB$.MODULE$;
        db.ensureInitialized();
        String name = "waffle_codegen_" + java.util.UUID.randomUUID().toString().replace("-", "");
        db.createTestDatabase(name);
        Configuration config = GenerationTool.load(Files.newInputStream(Paths.get("common/dao/src/main/resources/jooq-conf.xml")));
        config.setJdbc(new Jdbc().withDriver("org.postgresql.Driver")
            .withUrl(db.getDBInstance().getJdbcUrl("postgres", name))
            .withUser("postgres").withPassword(""));
        GenerationTool.generate(config);
        db.getDBInstance().close();
    }
}
