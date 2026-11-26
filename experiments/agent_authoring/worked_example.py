"""Sensitivity condition with one equivalent, solved wiring example per system."""
import json
EXAMPLES = {
    "waffle": [["input"], ["start",0,[]], ["emit",1,"x","y"], ["end",2,[["i","i+1"]],"i < 2"], ["sink",3]],
    "knime": [["input"], ["start",0], ["set",1,"i","i+1"], ["set",2,"flag","1 if i < 2 else 0"], ["keep",3,"flag"], ["end",1,4], ["sink",5]],
}
def documentation(system):
    return "\nWorked example on a DIFFERENT task: emit the unmodified input pair exactly twice. One valid complete graph is " + json.dumps(EXAMPLES[system]) + ". Your task follows. Construct your own graph."
