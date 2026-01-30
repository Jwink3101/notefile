Your task is to fully understand how the "eval" function currently works and develop a safer version that will be called safe_eval that will eventually replace eval.

The following is a basic guidline but if you think I am missing something, do not take this as completely strict or a full specification.

* Support python-like interface including "not", "and", "or", etc. including parethensis priorities
* Support "in" queries on text. If that needs to map to "grep", that is fine if documented
* Support current functions and thier "partials". Including grep, tall, tany, and the like
* Have the set-like object "tags" and be able to do set-like tests. E.G. "any(set(tag) == {'a','b'} for tag in tags)"
* Does *not* need to support the "note" object. The "data" dictionary is optiona but nice. But shoudl have "notes" (string), "tags" (set), and "test" (string)
* It would be nice to support multi-line with ';' as currently done but optional

Make sure to reference the full query help. See __init__'s query_help() function for the text

These should use inheritanly secure methods. I do not want to try to make "eval" or "exec" safe itself. Rather it should use capability to parse a new query language. If there remains safety gaps, please discuss when finished.

First make sure you fully understand the problem. Ask for help as needed. Then document in codex-material/QUERY_PLAN.md what you will do and how it will work. Then impliment. Do not stop unless you need human input to proceed.
