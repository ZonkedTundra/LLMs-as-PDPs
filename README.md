# Overview

This repo contains all the files required to reproduce the results reported in the paper. The codes within the repo support the claims that:

- LLMs can act as Policy Decision Points (PDP) in a small, well-specified smart home environment
- Performance degrades under ambiguous or incomplete queries
- Larger models improve accuracy but increase latency

While exact results may vary due to an LLM's non-deterministic behaviour, the trends should still match.

# Quick Start

1. Install LM Studio and enable Developer Mode
2. Load any supported model (e.g., qwen3-vl-4b)
3. Run: `python Simple.py`
4. Press `Enter` for all defaults

# Requirements

The results from the paper were run on a PC with: CPU: Intel i7-14700KF, GPU: Gigabyte 4060 Ti 8GB, RAM: DDR5 64GB 6000MHz. While identical specifications aren't required, latency results will vary depending on hardware. The main requirements are:

Required:

* OS: Windows/Mac/Linux
* Python version: >3.12.8
* LM Studio version: >0.4.4 (must support OpenAI-compatible Developer mode)

Optional:

* GPU: >8GB of VRAM
* RAM: >16GB (64GB used in experiments)

# Setup

First, download LM Studio ([download](https://lmstudio.ai/download)), which is used to run the LLM as a server. Once installed, enable `Developer mode` to allow you to create a server. Once in the developer tab enable the server and note where the models are accessible from (default: `http://127.0.0.1:1234`). If your application says otherwise then change it within the code.

When opening `http://127.0.0.1:1234` directly in a browser, you may see:

```json
{"error":"Unexpected endpoint or method. (GET /)"}
```

This is normal behaviour as the server expects a specific API endpoint, such as `/v1/models`, rather than the root URL. For example, `http://127.0.0.1:1234/v1/models` will return all downloaded models that can be loaded into the server.

Once the server is set up, download the appropriate models using the model search tab:

- qwen3-vl-4b: [https://lmstudio.ai/models/qwen/qwen3-vl-4b](https://lmstudio.ai/models/qwen/qwen3-vl-4b)
- gpt-oss-20b: [https://lmstudio.ai/models/openai/gpt-oss-20b](https://lmstudio.ai/models/openai/gpt-oss-20b)
- gpt-oss-120b: [https://lmstudio.ai/models/openai/gpt-oss-120b](https://lmstudio.ai/models/openai/gpt-oss-120b)

Once the models have downloaded, install a version of Python 3.12 or newer (no additional Python packages required).

# Run Experiments

```bash
python Simple.py
python Complex.py
python Complex_context_dropout.py
```

NOTE: Ensure LM Studio is running with the server reachable.

To run the programs, simply type python followed by the desired program into the terminal. Once started, the user will see 3 options.

* `model selection` - gives a list of the models tested in the paper, allowing you to choose a specific model (that will get loaded in) or use the model currently loaded into LM Studio
* `number of questions` - the default is 100; however, the user can specify a different value
* `inclusion of no occupants` - expects y if allowing for an empty House Occupants array or n to set the min size to 1 (default)

From there, the model will be asked a number of questions, with the terminal displaying the question, the oracle answer, the model answer, the match, and how long the response took.

While the default context length of 4096 is sufficient for these scenarios, if you decide to extend the policy set or use models with longer reasoning traces, consider increasing the context length in the model load settings (e.g. 8192) to reduce the risk of truncation.

# Execution Time

While the below time are averages using the defined hardware, they can vary drastically depending on what hardware and model the user selects.

- Simple:

  - Qwen3: ~8 seconds
  - GPT-OSS 20B: ~155 seconds
  - GPT-OSS 120B: ~381 seconds
- Complex:

  - Qwen3: ~10 seconds
  - GPT-OSS 20B: ~225 seconds
  - GPT-OSS 120B: ~760 seconds

# Expected Outputs

## Initial Setup

![1776435956194](image/README/1776435956194.png)

The model should first return the random seed, followed by a list of models to choose from. Once selected, the user is asked for the number of questions and an empty Occupants Array. All will accept an empty input and default to their corresponding values.

## Querying the Model

![1776435967431](image/README/1776435967431.png)

![1776436198602](image/README/1776436198602.png)

Whilst running the system returns each question after obtaining an answer. A match can either be `True` if both models agree or `False`.

## Summary Results

![1776435977349](image/README/1776435977349.png)

Once all the questions have been queried, a summary is printed that displays the overall accuracy, average time, macro-F1 scores, and a confusion matrix.

## Analysing Mistakes

![1776436013273](image/README/1776436013273.png)

This is the final input, where the user can decide to close the program after obtaining the results or get the model to explain its reasoning. If selected, the model will be provided with the question, the expected answer, and the model's answer. The model then returns a reason for the incorrect answer.

# Oracle schema

The `.xlsx` files structurally represent each scenario as formatted tables. In the code, these files are converted into two forms: a matrix for reproducing ground-truth answers, and natural-language policies used by the LLMs.

## Simple Oracle

The simple oracle is a device-by-user permission matrix. Rows represent devices and columns represent users. Permissions are denoted as `Y` or `1` for Permit, and `N` or `0` for Deny.

In `Simple.py`, the matrix is accessed via `oracle[device_idx][user_idx]`. If the device query contains no valid user, the ground truth is set to Deny.

## Complex Oracle

The complex oracle uses the same device-by-user structure, but each cell can now contain one or more rule IDs rather than a direct Permit/Deny value. A cell that contains `M` or a collection of numbers other than `0` or `1` refers to specific rules that must hold for the user to be granted access to the device. The meaning of each rule ID is defined within the code just above the oracle definition.

When a query is generated, the system calls `rule_checker`, which is a hard-coded function that evaluates the current environment against the relevant rules. The checker follows a Deny-Unless-Permit approach, meaning access is denied unless one of the applicable rules grants access.

# Reproducing Paper Results

Due to the probabilistic nature of LLMs, exact scores may vary between runs. To approximate the values reported within the paper, utilise multiple random seeds and re-runs to create an average scores. While the scores will be different the observed trends should still match the paper.
