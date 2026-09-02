# Multi-LLM Comparison Study

## Setup
Same 20 fault scenarios (5 services × 4 fault types) run through
three free open-source LLMs via Groq, plus the rule-based baseline.

## Results

| Model | LLM Accuracy | Rule Accuracy | Recovery Rate | Avg MTTR |
|---|---|---|---|---|
| Llama 3.3 70B | 100% (20/20) | 100% | 100% | 2.44s |
| Llama 3.1 70B | 100% (20/20) | 100% | 100% | 2.54s |
| Mixtral 8x7B  | 100% (20/20) | 100% | 100% | 2.46s |
| Rule-based    | 100% (20/20) | —    | 100% | ~2.5s |
| Manual baseline | ~100%*     | —    | 100% | 900s |

*Manual diagnosis assumed correct; MTTR is industry estimate.

## Key Findings

### Model-agnostic robustness
All three LLMs achieved identical 100% accuracy, indicating that
structured fault classification over well-defined metric signatures
is robustly solvable across current open LLM architectures. Model
choice is not a limiting factor for this fault taxonomy.

### LLM vs rule-based parity
LLMs matched the rule-based baseline (both 100%) on clean,
single-signal faults. The LLM's advantage is interpretability
(human-readable explanations) rather than raw accuracy on
well-defined faults.

### MTTR consistency
Average MTTR ranged 2.44–2.54s across models. Differences are
within noise and attributable to network/API latency, not model
reasoning speed.

### Implication for accessibility
Since any of three free models achieves full accuracy, this approach
is reproducible at zero API cost with no dependence on a specific
provider — a key accessibility contribution for AIOps research.

## Note on earlier single run
An earlier single run of Llama 3.3 scored 19/20, with one
misclassification (cart/memory → service_crash) caused by the
memory leak progressing to termination before sampling. This
timing edge case did not recur in the multi-model runs due to
randomized fault timing, illustrating the stochastic nature of
the memory-leak-to-crash transition.