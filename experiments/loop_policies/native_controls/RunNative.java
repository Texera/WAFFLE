import com.rapidminer.Process;
import com.rapidminer.RapidMiner;
import com.rapidminer.example.Example;
import com.rapidminer.example.ExampleSet;
import com.rapidminer.operator.IOObjectCollection;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/** Observe the result collection after the saved process has finished. */
public class RunNative {
    public static void main(String[] args) throws Exception {
        RapidMiner.setExecutionMode(RapidMiner.ExecutionMode.EMBEDDED_WITHOUT_UI);
        RapidMiner.init();
        Process process = new Process(new File(args[0]));
        IOObjectCollection<?> result = (IOObjectCollection<?>) process.run().getElementAt(0);
        List<String> rows = new ArrayList<>();
        for (Object member : result.getObjects()) {
            ExampleSet set = (ExampleSet) member;
            for (Example row : set) {
                rows.add("{\"K\":" + row.getValue(set.getAttributes().get("K"))
                        + ",\"score\":" + row.getValue(set.getAttributes().get("score")) + "}");
            }
        }
        Files.writeString(Path.of(args[1]), "{\"iterations\":" + process.getOperator("Body").getApplyCount()
                + ",\"rows\":[" + String.join(",",rows) + "]}");
        System.exit(0);
    }
}
