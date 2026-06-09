# Datum to test the previously unreached `a=NAME '=' b=expression` in kwarg_or_double_starred
print("a", "b", sep="", **{"end": "!!!"})