"""Reproduce the blog's toy attention example; Python 3.10+, no dependencies."""
import math


def attention(queries, keys, values, *, causal=False):
    """One attention head with a row-wise softmax; inputs are nested lists.

    This small example expects nonempty, rectangular matrices. For a causal
    mask, query and key positions must refer to the same aligned sequence.
    """
    if not queries or not keys or len(keys) != len(values):
        raise ValueError("Nonempty queries, keys, and matching values required")
    key_width = len(keys[0])
    value_width = len(values[0])
    if not key_width or not value_width:
        raise ValueError("Vector widths must be positive")
    if any(len(row) != key_width for row in queries + keys):
        raise ValueError("Queries and keys must have the same vector width")
    if any(len(row) != value_width for row in values):
        raise ValueError("Values must have a consistent vector width")
    if causal and len(queries) != len(keys):
        raise ValueError("This causal example requires equal sequence lengths")

    weights, outputs = [], []
    for i, query in enumerate(queries):
        scores = [
            -math.inf if causal and j > i else
            sum(q * k for q, k in zip(query, key)) / math.sqrt(key_width)
            for j, key in enumerate(keys)
        ]
        peak = max(scores)
        exponentials = [math.exp(score - peak) for score in scores]
        total = sum(exponentials)
        row = [value / total for value in exponentials]
        weights.append(row)
        outputs.append([
            sum(weight * value[d] for weight, value in zip(row, values))
            for d in range(value_width)
        ])
    return weights, outputs


def main():
    queries = [[0, 1], [1, 0], [1, 1]]
    keys = [[1, 0], [0, 1], [1, 1]]
    values = [[2, 0], [0, 2], [2, 2]]
    weights, outputs = attention(queries, keys, values)
    print("坐 attention:", [round(value, 4) for value in weights[1]])
    print("坐 output:   ", [round(value, 4) for value in outputs[1]])
    assert all(math.isclose(sum(row), 1.0) for row in weights)
    assert math.isclose(outputs[1][0], 1.6044483706441307)
    assert math.isclose(outputs[1][1], 1.1977758146779347)

    masked, _ = attention(queries, keys, values, causal=True)
    assert all(math.isclose(sum(row), 1.0) for row in masked)
    assert all(masked[i][j] == 0.0 for i in range(3) for j in range(i + 1, 3))
    assert masked[0] == [1.0, 0.0, 0.0]
    print("Row sums and causal mask: OK")


if __name__ == "__main__":
    main()
