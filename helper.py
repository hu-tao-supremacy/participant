from google.protobuf import wrappers_pb2 as wrapper
import base64

def getInt64Value(value):
    if value is None:
        return None
    temp = wrapper.Int64Value()
    temp.value = value
    return temp

def b64encode(data):
    encodedBytes = base64.b64encode(data.encode("utf-8"))
    return str(encodedBytes, "utf-8")