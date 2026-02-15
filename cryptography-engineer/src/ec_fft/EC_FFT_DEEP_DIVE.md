# EC-FFT: A Deep Dive

## Table of Contents

1. [What Is EC-FFT?](#1-what-is-ec-fft)
2. [Prerequisites: Concepts You Need](#2-prerequisites-concepts-you-need)
3. [Standard FFT Recap](#3-standard-fft-recap)
4. [From Scalar FFT to EC-FFT](#4-from-scalar-fft-to-ec-fft)
5. [The Butterfly Algorithm, Step by Step](#5-the-butterfly-algorithm-step-by-step)
6. [Walking Through the Code](#6-walking-through-the-code)
7. [The SRS Conversion: Why EC-FFT Matters](#7-the-srs-conversion-why-ec-fft-matters)
8. [Inverse EC-FFT](#8-inverse-ec-fft)
9. [Complexity Analysis](#9-complexity-analysis)
10. [Test Suite Walkthrough](#10-test-suite-walkthrough)
11. [Common Pitfalls and Gotchas](#11-common-pitfalls-and-gotchas)

---

## 1. What Is EC-FFT?

EC-FFT (**Elliptic Curve Fast Fourier Transform**) is the Fast Fourier Transform
algorithm adapted to work on **elliptic curve points** instead of field elements
(scalars).

In a standard FFT, you take a vector of field elements and evaluate the
corresponding polynomial at every *n*-th root of unity. In EC-FFT, you take a
vector of **curve points** — each of which is some unknown scalar times a
generator — and produce a new vector of curve points that corresponds to
evaluating the same "hidden" polynomial at the roots of unity, but entirely
within the curve group.

**The key insight**: You never learn the underlying scalars. You only manipulate
the curve points. Yet the output is mathematically equivalent to what you would
get if you *could* extract the scalars, run a normal FFT on them, and then
multiply each result by the generator.

---

## 2. Prerequisites: Concepts You Need

### 2.1 Finite Fields

A finite field **F_p** is a set of integers {0, 1, ..., p−1} equipped with
addition and multiplication modulo a prime *p*. Every nonzero element has a
multiplicative inverse. In our code, the type `fr` represents elements of the
BN254 scalar field.

### 2.2 Roots of Unity

An *n*-th root of unity is an element ω ∈ F_p such that ω^n = 1. When *n* is a
power of two and the field order *p* supports it (i.e., n | (p−1)), there exists
a **primitive** *n*-th root of unity ω where:

```
{ω^0, ω^1, ω^2, ..., ω^(n-1)} are all distinct
```

These *n* values form a multiplicative subgroup and are the "evaluation points"
used by FFT.

### 2.3 Elliptic Curve Groups

An elliptic curve group **G₁** over a finite field consists of points (x, y)
satisfying a curve equation (e.g., y² = x³ + 3 for BN254), plus a point at
infinity. The group operation is **point addition**, written `P + Q`.

**Scalar multiplication** is repeated addition: `k · P = P + P + ... + P` (*k*
times). In our code:

- `g1::element` — a curve point in **projective coordinates** (x, y, z)
- `g1::affine_element` — a curve point in **affine coordinates** (x, y)
- `g1::one` — the fixed generator G₁

### 2.4 Coordinate Systems

| Representation | Fields | Addition Cost | Why Use It? |
|---|---|---|---|
| Affine (x, y) | 2 | Requires modular inversion | Compact storage |
| Projective (X, Y, Z) | 3 | No inversions needed | Fast arithmetic |

EC-FFT works in projective coordinates internally because it performs many
additions. The `convert_srs` function converts affine → projective at the start
and projective → affine at the end.

---

## 3. Standard FFT Recap

### 3.1 The Problem

Given a polynomial in coefficient form:

```
f(X) = f₀ + f₁·X + f₂·X² + ... + f_{n-1}·X^{n-1}
```

Evaluate it at all *n*-th roots of unity:

```
f(ω⁰), f(ω¹), f(ω²), ..., f(ω^{n-1})
```

Naively this costs O(n²). FFT does it in **O(n log n)**.

### 3.2 The Cooley-Tukey Butterfly

The key identity: split the polynomial into even and odd terms.

```
f(X) = f_even(X²) + X · f_odd(X²)
```

where:
```
f_even(Y) = f₀ + f₂·Y + f₄·Y² + ...
f_odd(Y)  = f₁ + f₃·Y + f₅·Y² + ...
```

Because (ω^k)² = (ω^{k+n/2})², each half-size FFT can be reused for two
outputs. This gives the recurrence T(n) = 2·T(n/2) + O(n), yielding O(n log n).

### 3.3 Iterative (Bottom-Up) FFT

The recursive version is elegant but impractical (function call overhead, poor
cache locality). The iterative version:

1. **Bit-reverse** the input array
2. **Butterfly stages**: for block sizes 2, 4, 8, ..., n, combine pairs using
   twiddle factors (roots of unity)

Each butterfly operation on a pair (a, b) with twiddle factor ω computes:

```
a' = a + ω·b
b' = a - ω·b
```

This is the fundamental "butterfly" — it takes two inputs and produces two
outputs using one multiplication and two additions.

---

## 4. From Scalar FFT to EC-FFT

The beautiful observation is that the FFT butterfly:

```
a' = a + ω·b       (scalar version)
b' = a - ω·b
```

maps directly to curve operations:

```
A' = A + ω·B       (EC version: A, B are curve points; ω is a scalar)
B' = A - ω·B
```

Here:
- `A + (...)` is **elliptic curve point addition**
- `A - (...)` is **elliptic curve point subtraction**
- `ω · B` is **scalar multiplication** of curve point B by field element ω

The algorithm structure is **identical**. Only the underlying algebraic
operations change:

| Operation | Scalar FFT | EC-FFT |
|---|---|---|
| "Multiply" by twiddle | Field multiplication (fast) | Scalar-point multiplication (expensive!) |
| "Add" two values | Field addition (very fast) | Point addition (moderate) |
| "Subtract" two values | Field subtraction (very fast) | Point subtraction (moderate) |

This is why EC-FFT is **much slower** than scalar FFT — scalar multiplication on
a curve is orders of magnitude more expensive than field multiplication.

---

## 5. The Butterfly Algorithm, Step by Step

### Visual Example: n = 8

After bit-reversal, the indices are reordered:

```
Original:     [0] [1] [2] [3] [4] [5] [6] [7]
Bit-reversed: [0] [4] [2] [6] [1] [5] [3] [7]
```

Then we apply butterfly stages:

```
Stage 0 (m=1): Pairs with twiddle = 1 (no scalar mul needed)
  ┌─────────────────────────────────────────────┐
  │ (0,1) (2,3) (4,5) (6,7)                    │
  │  Each pair: (a,b) → (a+b, a-b)             │
  └─────────────────────────────────────────────┘

Stage 1 (m=2): Blocks of 4, root_table[0]
  ┌─────────────────────────────────────────────┐
  │ Block [0..3]:                               │
  │   (0,2) with root_table[0][0]               │
  │   (1,3) with root_table[0][1]               │
  │ Block [4..7]:                               │
  │   (4,6) with root_table[0][0]               │
  │   (5,7) with root_table[0][1]               │
  └─────────────────────────────────────────────┘

Stage 2 (m=4): One block of 8, root_table[1]
  ┌─────────────────────────────────────────────┐
  │ Block [0..7]:                               │
  │   (0,4) with root_table[1][0]               │
  │   (1,5) with root_table[1][1]               │
  │   (2,6) with root_table[1][2]               │
  │   (3,7) with root_table[1][3]               │
  └─────────────────────────────────────────────┘
```

### The Root Table

The `root_table` stores precomputed roots of unity for each stage:

```
root_table[0]: ω₄⁰, ω₄¹               (2 entries, 4th roots of unity)
root_table[1]: ω₈⁰, ω₈¹, ω₈², ω₈³    (4 entries, 8th roots of unity)
...
root_table[r]: entries for the (r+2)-th stage
```

where ω_k denotes a primitive k-th root of unity. At stage *r*, the twiddle
factor for position *j* within a half-block is `root_table[r][j]`.

---

## 6. Walking Through the Code

### 6.1 `ec_fft_inner` — The Core Algorithm

```cpp
void ec_fft_inner(g1::element* g1_elements, const size_t n,
                  const std::vector<fr*>& root_table)
```

**Phase 1: Bit-Reversal Permutation** (lines 50–66)

```cpp
// Compute log2(n)
uint32_t log2_n = 0;
size_t temp_n = n;
while (temp_n > 1) { temp_n >>= 1; log2_n++; }

// Swap each element with its bit-reversed partner
for (uint32_t i = 0; i < n; ++i) {
    uint32_t j = reverse_bits(i, log2_n);
    if (i < j) {                           // Only swap once per pair
        g1::element temp = g1_elements[i];
        g1_elements[i] = g1_elements[j];
        g1_elements[j] = temp;
    }
}
```

The `reverse_bits` helper reverses the lowest `log2_n` bits of an integer using
a series of bitmask swaps — a classic O(1) bit-reversal trick.

**Phase 2: First Butterfly Stage** (lines 87–91)

```cpp
for (size_t k = 0; k < n; k += 2) {
    g1::element temp = g1_elements[k + 1];
    g1_elements[k + 1] = g1_elements[k] - temp;
    g1_elements[k] += temp;
}
```

Why special-case this? Because the twiddle factor is always 1 (ω₂⁰ = 1), so we
skip the scalar multiplication entirely. Since scalar-point multiplication is by
far the most expensive operation, this optimization is significant.

**Phase 3: Remaining Stages** (lines 135–148)

```cpp
size_t round = 0;
for (size_t m = 2; m < n; m *= 2) {           // m = half-block size
    for (size_t k = 0; k < n; k += (2 * m)) { // k = block start
        for (size_t j = 0; j < m; ++j) {       // j = position in half-block
            size_t even_idx = k + j;
            size_t odd_idx  = k + j + m;
            fr root = root_table[round][j];
            g1::element temp = g1_elements[odd_idx] * root;  // SCALAR MUL
            g1_elements[odd_idx]  = g1_elements[even_idx] - temp;  // POINT SUB
            g1_elements[even_idx] += temp;                         // POINT ADD
        }
    }
    round++;
}
```

This is the textbook iterative Cooley-Tukey FFT, with field multiplications
replaced by scalar-point multiplications and field additions replaced by point
additions.

### 6.2 `ec_fft` and `ec_ifft` — Public Interface

```cpp
void ec_fft(g1::element* g1_elements, const evaluation_domain& domain) {
    ec_fft_inner(g1_elements, domain.size, domain.get_round_roots());
}

void ec_ifft(g1::element* g1_elements, const evaluation_domain& domain) {
    ec_fft_inner(g1_elements, domain.size, domain.get_inverse_round_roots());
    for (size_t i = 0; i < domain.size; i++) {
        g1_elements[i] *= domain.domain_inverse;  // Scale by 1/n
    }
}
```

The inverse FFT uses **inverse roots of unity** (ω⁻¹ instead of ω) and then
scales every output by 1/n. This mirrors exactly how inverse scalar FFT works.

### 6.3 `convert_srs` — The Real-World Application

This function converts a monomial SRS to a Lagrange SRS:

```
Input:  { [1]₁, [x]₁, [x²]₁, ..., [x^{n-1}]₁ }
Output: { [L₀(x)]₁, [L₁(x)]₁, ..., [L_{n-1}(x)]₁ }
```

**Step 1**: Copy affine points into projective working array.

**Step 2**: Apply `ec_fft()` → now `work[k] = [P(ω^k)]₁`.

**Step 3**: Rearrange and scale:
```cpp
for (size_t i = 0; i < n; i++) {
    size_t idx = (n - i) % n;
    g1::element scaled = work[idx] * domain.domain_inverse;
    lagrange_srs[i] = g1::affine_element(scaled);
}
```

The index mapping `(n - i) % n` comes from the identity ω^{-i} = ω^{n-i},
and the 1/n scaling comes from the Lagrange basis formula.

---

## 7. The SRS Conversion: Why EC-FFT Matters

### 7.1 The Problem

In zkSNARK systems like PlonK, a **trusted setup ceremony** produces a
Structured Reference String (SRS) in **monomial form**:

```
Monomial SRS = { [1]₁, [x]₁, [x²]₁, ..., [x^{n-1}]₁ }
```

where *x* is a secret that nobody knows (it was destroyed after the ceremony).

To commit to a polynomial `f(X) = Σ fᵢ·Xⁱ`, you compute:

```
commit(f) = Σ fᵢ · [xⁱ]₁ = [f(x)]₁
```

But PlonK's prover internally works with polynomials in **Lagrange form**
(values at roots of unity, not coefficients). To commit in Lagrange form, you
need a **Lagrange SRS**:

```
Lagrange SRS = { [L₀(x)]₁, [L₁(x)]₁, ..., [L_{n-1}(x)]₁ }
```

Then committing a polynomial given its evaluations {f(ω⁰), f(ω¹), ...} is:

```
commit(f) = Σ f(ωⁱ) · [Lᵢ(x)]₁ = [f(x)]₁
```

The two commitments are identical — same curve point — but the Lagrange version
avoids an iFFT during proving, saving significant time.

### 7.2 The Mathematical Bridge

Define the polynomial:

```
P(Y) = 1 + x·Y + x²·Y² + ... + x^{n-1}·Y^{n-1} = Σⱼ (x·Y)ʲ
```

The Lagrange basis polynomial has the closed form:

```
L_{n,i}(X) = (1/n) · Σⱼ (ω^{-i} · X)ʲ
```

Evaluating at X = x:

```
L_{n,i}(x) = (1/n) · Σⱼ (ω^{-i} · x)ʲ = (1/n) · P(ω^{-i})
```

So: **evaluating the Lagrange basis at the secret x is the same as evaluating
P at the inverse roots of unity, scaled by 1/n.** And evaluating P at all
roots of unity is exactly what FFT does!

### 7.3 The Algorithm

```
                    EC-FFT                     Index remap + scale
Monomial SRS  ──────────────→  {[P(ωᵏ)]₁}  ──────────────────────→  Lagrange SRS
```

1. Treat the monomial SRS points as "coefficients" of P(Y)
2. Apply EC-FFT to evaluate P at {ω⁰, ω¹, ..., ω^{n-1}}
3. For each i: `[L_{n,i}(x)]₁ = (1/n) · [P(ω^{n-i mod n})]₁`

The entire conversion happens **without ever knowing x**.

---

## 8. Inverse EC-FFT

The inverse EC-FFT recovers the original "coefficient" points from their
"evaluation" points. It works identically to inverse scalar FFT:

1. Run the same butterfly algorithm but with **inverse roots** (ω⁻¹ instead of ω)
2. Scale every output point by **1/n** (as a scalar multiplication)

```cpp
void ec_ifft(g1::element* g1_elements, const evaluation_domain& domain) {
    ec_fft_inner(g1_elements, domain.size, domain.get_inverse_round_roots());
    for (size_t i = 0; i < domain.size; i++) {
        g1_elements[i] *= domain.domain_inverse;   // *= 1/n
    }
}
```

**Why it works**: The DFT matrix using roots ω has an inverse that is (1/n)
times the DFT matrix using roots ω⁻¹. This algebraic identity carries over
unchanged to the curve setting.

---

## 9. Complexity Analysis

### Time Complexity

| Operation | Count | Unit Cost | Total |
|---|---|---|---|
| Bit-reversal swaps | O(n) | O(1) per swap | O(n) |
| Stage 0 butterflies | n/2 | 1 point add + 1 point sub | O(n) group ops |
| Stages 1..log₂n−1 butterflies | (n/2)·(log₂n − 1) | 1 scalar mul + 1 point add + 1 point sub | O(n log n) scalar muls |

**Dominant cost**: O(n log n) **scalar multiplications**, each of which is
roughly 250× more expensive than a field multiplication (for a 254-bit scalar on
BN254).

For comparison:
- Scalar FFT: O(n log n) field multiplications
- EC-FFT: O(n log n) scalar-point multiplications (~250× slower per operation)

### Space Complexity

- O(n) for the working array of curve points
- The root table is shared with scalar FFT infrastructure and is precomputed

---

## 10. Test Suite Walkthrough

The test file `ec_fft.test.cpp` contains four tests that validate correctness:

### Test 1: `test_fft_ifft` — Round-Trip Identity

```
Points → ec_fft → ec_ifft → Same points?
```

Verifies that FFT followed by inverse FFT returns the original points. This is
the most fundamental correctness check.

### Test 2: `test_compare_ffts` — EC-FFT vs Scalar FFT

```
Random scalars aᵢ → Points Pᵢ = aᵢ·G₁
                    ↓
              EC-FFT on Pᵢ     vs.     Scalar FFT on aᵢ, then multiply by G₁
                    ↓                          ↓
              Same results?  ←─────────────────┘
```

If `a = (a₀, a₁, ..., a_{n-1})` and `FFT(a) = (b₀, b₁, ..., b_{n-1})`, then
`EC-FFT(a₀·G, a₁·G, ...) = (b₀·G, b₁·G, ...)`. This test verifies exactly that.

### Test 3: `test_compare_iffts` — Same as Test 2, but for Inverse FFT

Validates that EC-iFFT matches scalar iFFT in the same way.

### Test 4: `test_convert_srs` — End-to-End SRS Conversion

The most comprehensive test:
1. Generate a fake SRS with a known secret *x*
2. Convert monomial SRS → Lagrange SRS using `convert_srs`
3. Commit to a random polynomial using both:
   - Monomial form with monomial SRS (via Pippenger multi-scalar multiplication)
   - Lagrange form with Lagrange SRS (via Pippenger)
4. Verify both commitments produce the **same curve point**

This proves the Lagrange SRS is correct — if the commitment matches, the
Lagrange basis points must be right.

---

## 11. Common Pitfalls and Gotchas

### 11.1 Affine vs. Projective Coordinates

EC-FFT must operate on `g1::element` (projective), not `g1::affine_element`.
The `convert_srs` function handles the conversion at boundaries. Forgetting to
convert will cause compilation errors or incorrect results.

### 11.2 The Index Remap in `convert_srs`

The mapping `lagrange_srs[i] = (1/n) · work[(n - i) % n]` is easy to get wrong.
The `(n - i) % n` arises because we need P(ω^{-i}) but the FFT gives us
P(ω^{+k}). Since ω^{-i} = ω^{n-i}, we look up index `n - i` (with mod n to
handle the i=0 case, where n-0 = n wraps to 0).

### 11.3 Stage 0 Optimization

The first butterfly stage skips scalar multiplication because the twiddle factor
is 1. If you accidentally include the scalar multiplication for this stage, the
code will still be correct but noticeably slower — especially for large n.

### 11.4 Root Table Indexing

The root table is offset by one stage: `root_table[0]` corresponds to the
**second** butterfly stage (m=2), not the first (m=1). The first stage has no
entry because its twiddle factor is always 1.

### 11.5 In-Place Operation

Both `ec_fft` and `ec_ifft` modify the input array **in-place**. If you need the
original data, copy it before calling. The `convert_srs` function does this
internally with its `work` vector.

---

## Summary

EC-FFT is a direct, elegant lifting of the classical Cooley-Tukey FFT from
scalar arithmetic to elliptic curve group operations. The algorithm structure is
identical — bit-reversal, then log₂(n) stages of butterfly operations — but each
butterfly uses scalar-point multiplication instead of field multiplication and
point addition instead of field addition.

Its primary application in practice is converting a monomial SRS (output of a
trusted setup ceremony) into a Lagrange SRS, enabling faster polynomial
commitment during zkSNARK proving. The conversion is made possible by the
mathematical identity linking Lagrange basis polynomials to evaluations of a
generating polynomial P(Y) at roots of unity — an evaluation that is precisely
what FFT computes.
