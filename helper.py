from google.protobuf import wrappers_pb2 as wrapper

def getInt64Value(value):
    temp = wrapper.Int64Value()
    temp.value = value
    return temp