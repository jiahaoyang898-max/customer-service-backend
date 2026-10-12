condition = "context.get('reason') == 'xyz'"
data = {
    "context": {"reason": "abc"}
}
print(bool(eval(condition,  data)))