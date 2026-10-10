## 1: Change the argv and stdin in judge()

- The model flag always appears as `"--model"` followed by the model name. (Tess)
- Appending the sentinel to `cmd` keeps 00034's no-leak assertion meaningful, because the sentinel is the only slice-like text it looks for. (Tess)
- Every `fake_run` that reads `kwargs["input"]` is only called through `judge()` with `input=`. (Tess)
