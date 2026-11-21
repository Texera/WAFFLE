import com.rapidminer.Process;
import com.rapidminer.RapidMiner;
import com.rapidminer.example.Attribute;
import com.rapidminer.example.Example;
import com.rapidminer.example.ExampleSet;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Run one saved process and export its actual result port and body execution count. */
public class RunProcess {
    public static void main(String[] args) throws Exception {
        RapidMiner.setExecutionMode(RapidMiner.ExecutionMode.EMBEDDED_WITHOUT_UI);
        RapidMiner.init();
        Process process = new Process(new File(args[0]));
        ExampleSet result = (ExampleSet) process.run().getElementAt(0);
        Attribute payload = result.getAttributes().get("payload");
        List<String> rows = new ArrayList<>();
        for (Example row : result) {
            rows.add(row.getValueAsString(payload));
        }
        String json = "{\"version\":\"" + RapidMiner.getVersion() + "\",\"iterations\":"
                + process.getOperator("Body").getApplyCount()
                + ",\"rows\":[" + String.join(",\n", rows) + "]}";
        Files.writeString(Path.of(args[1]), json, StandardCharsets.UTF_8);
        System.exit(0);
    }
}
