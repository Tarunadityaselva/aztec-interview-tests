#include "ec_fft.hpp"

#pragma GCC diagnostic ignored "-Wunused-variable"
#pragma GCC diagnostic ignored "-Wunused-parameter"

namespace waffle {
namespace g1_fft {

using namespace barretenberg;

inline bool is_power_of_two(uint64_t x)
{
    return x && !(x & (x - 1));
}

inline uint32_t reverse_bits(uint32_t x, uint32_t bit_length)
{
    x = (((x & 0xaaaaaaaa) >> 1) | ((x & 0x55555555) << 1));
    x = (((x & 0xcccccccc) >> 2) | ((x & 0x33333333) << 2));
    x = (((x & 0xf0f0f0f0) >> 4) | ((x & 0x0f0f0f0f) << 4));
    x = (((x & 0xff00ff00) >> 8) | ((x & 0x00ff00ff) << 8));
    return (((x >> 16) | (x << 16))) >> (32 - bit_length);
}

inline void ec_fft_inner(g1::element* g1_elements, const size_t n, const std::vector<fr*>& root_table)
{
    is_power_of_two(n);
    ASSERT(!root_table.empty());

    // =========================================================================
    // STEP 1: Bit-Reversal Permutation
    // =========================================================================
    //
    // The iterative Cooley-Tukey FFT requires the input to be reordered so that
    // the element at position i is moved to position bit_reverse(i).
    //
    // WHY: The recursive FFT splits the array into even-indexed and odd-indexed
    // halves at every level. When you "unroll" this recursion into an iterative
    // bottom-up algorithm, the leaf-level ordering corresponds exactly to the
    // bit-reversal of the original indices.
    //
    // EXAMPLE for n=8 (3-bit indices):
    //   Original index: 0(000) 1(001) 2(010) 3(011) 4(100) 5(101) 6(110) 7(111)
    //   Bit-reversed:   0(000) 4(100) 2(010) 6(110) 1(001) 5(101) 3(011) 7(111)
    //
    // We compute log2(n) to know how many bits each index has.
    // The helper `reverse_bits(i, log2_n)` reverses the lowest `log2_n` bits of i.
    // We only swap when i < j to avoid swapping the same pair twice.
    //
    uint32_t log2_n = 0;
    {
        size_t temp_n = n;
        while (temp_n > 1) {
            temp_n >>= 1;
            log2_n++;
        }
    }

    for (uint32_t i = 0; i < n; ++i) {
        uint32_t j = reverse_bits(i, log2_n);
        if (i < j) {
            g1::element temp = g1_elements[i];
            g1_elements[i] = g1_elements[j];
            g1_elements[j] = temp;
        }
    }

    // =========================================================================
    // STEP 2: First Butterfly Stage (half-block size m = 1)
    // =========================================================================
    //
    // In the first stage, we combine pairs of single elements into 2-element
    // DFTs. The twiddle factor (root of unity) for this stage is always 1,
    // because the only root of a size-2 DFT at position j=0 is ω_2^0 = 1.
    //
    // The butterfly operation with root = 1 simplifies to:
    //     temp         = g1_elements[k + 1]  (no multiplication needed)
    //     g1_elements[k + 1] = g1_elements[k] - temp   (the "odd" output)
    //     g1_elements[k]    += temp                     (the "even" output)
    //
    // This is equivalent to: (a, b) → (a + b, a - b)
    //
    // We handle this stage separately because skipping the scalar multiplication
    // (which is the most expensive operation on curve points) saves significant
    // computation.
    //
    for (size_t k = 0; k < n; k += 2) {
        g1::element temp = g1_elements[k + 1];
        g1_elements[k + 1] = g1_elements[k] - temp;
        g1_elements[k] += temp;
    }

    // =========================================================================
    // STEP 3: Remaining Butterfly Stages (m = 2, 4, 8, ..., n/2)
    // =========================================================================
    //
    // For each subsequent stage, we combine pairs of sub-DFTs into larger DFTs.
    //
    // VARIABLES:
    //   m     = half the block size at this stage. We combine two sub-DFTs of
    //           size m into one DFT of size 2m.
    //   round = index into root_table for this stage.
    //           root_table[0] has 2 entries  → used when m=2  (stage 1)
    //           root_table[1] has 4 entries  → used when m=4  (stage 2)
    //           root_table[r] has 2^(r+1)    → used when m=2^(r+1) (stage r+1)
    //   k     = starting index of each block of size 2m
    //   j     = position within the half-block (0 to m-1)
    //
    // THE BUTTERFLY OPERATION (for each pair):
    //
    //   root = root_table[round][j]     ← the "twiddle factor" for this position
    //
    //   The twiddle factor at position j in a stage combining into size-2m DFTs
    //   is ω_{2m}^j, i.e., the j-th power of the (2m)-th primitive root of unity.
    //   These are precomputed in root_table.
    //
    //   temp = root * g1_elements[odd_idx]    ← SCALAR MULTIPLICATION of a curve
    //                                            point by a field element
    //   g1_elements[odd_idx]  = g1_elements[even_idx] - temp  ← POINT SUBTRACTION
    //   g1_elements[even_idx] += temp                          ← POINT ADDITION
    //
    // This is the exact same butterfly as scalar FFT, but with:
    //   - Scalar multiplication (root * point) instead of field multiplication
    //   - Elliptic curve point addition/subtraction instead of field add/sub
    //
    // VISUAL for n=8:
    //
    //   Stage 1 (m=2): blocks of 4, root_table[0]
    //     Block [0..3]: pairs (0,2) with root[0], (1,3) with root[1]
    //     Block [4..7]: pairs (4,6) with root[0], (5,7) with root[1]
    //
    //   Stage 2 (m=4): blocks of 8, root_table[1]
    //     Block [0..7]: pairs (0,4) root[0], (1,5) root[1], (2,6) root[2], (3,7) root[3]
    //
    size_t round = 0;
    for (size_t m = 2; m < n; m *= 2) {
        for (size_t k = 0; k < n; k += (2 * m)) {
            for (size_t j = 0; j < m; ++j) {
                size_t even_idx = k + j;
                size_t odd_idx = k + j + m;
                fr root = root_table[round][j];
                g1::element temp = g1_elements[odd_idx] * root;
                g1_elements[odd_idx] = g1_elements[even_idx] - temp;
                g1_elements[even_idx] += temp;
            }
        }
        round++;
    }
}

void ec_fft(g1::element* g1_elements, const evaluation_domain& domain)
{
    ec_fft_inner(g1_elements, domain.size, domain.get_round_roots());
}

void ec_ifft(g1::element* g1_elements, const evaluation_domain& domain)
{
    ec_fft_inner(g1_elements, domain.size, domain.get_inverse_round_roots());
    for (size_t i = 0; i < domain.size; i++) {
        g1_elements[i] *= domain.domain_inverse;
    }
}

void convert_srs(g1::affine_element* monomial_srs, g1::affine_element* lagrange_srs, const evaluation_domain& domain)
{
    const size_t n = domain.size;
    is_power_of_two(n);

    // =========================================================================
    // CONVERTING MONOMIAL SRS TO LAGRANGE SRS
    // =========================================================================
    //
    // INPUT:  monomial_srs = { [1]₁, [x]₁, [x²]₁, ..., [x^(n-1)]₁ }
    //         These are elliptic curve points where the i-th point is xⁱ·G₁.
    //         We do NOT know the secret scalar x.
    //
    // OUTPUT: lagrange_srs = { [L₀(x)]₁, [L₁(x)]₁, ..., [L_{n-1}(x)]₁ }
    //         where Lᵢ(X) is the i-th Lagrange basis polynomial over the
    //         n-th roots of unity.
    //
    // THE KEY MATHEMATICAL INSIGHT:
    //
    //   Define the polynomial P(Y) = 1 + xY + x²Y² + ... + x^(n-1)·Y^(n-1)
    //                               = Σⱼ (xY)ʲ
    //
    //   The monomial SRS points [1]₁, [x]₁, [x²]₁, ... are exactly the
    //   "coefficients" of P(Y) — but as curve points, not raw scalars.
    //
    //   The Lagrange basis polynomial can be written as:
    //     L_{n,i}(X) = (1/n) · Σⱼ (ω^{-i} · X)ʲ
    //
    //   Evaluating at X = x:
    //     L_{n,i}(x) = (1/n) · Σⱼ (ω^{-i} · x)ʲ = (1/n) · P(ω^{-i})
    //
    //   So if we can compute P(ω^k) for all k (which is exactly what FFT does),
    //   we can recover L_{n,i}(x) by:
    //     [L_{n,i}(x)]₁ = (1/n) · [P(ω^{-i})]₁
    //
    // ALGORITHM:
    //
    //   1. Copy monomial SRS into a working array of projective points
    //      (g1::element) because EC-FFT operates on projective coordinates.
    //
    //   2. Apply ec_fft() to get:
    //        work[k] = [P(ω^k)]₁   for k = 0, 1, ..., n-1
    //
    //   3. For each i, compute:
    //        lagrange_srs[i] = (1/n) · work[(n - i) % n]
    //
    //      The index mapping (n - i) % n is because:
    //        ω^{-i} = ω^{n-i}   (since ω^n = 1)
    //      So [P(ω^{-i})]₁ = work[(n - i) mod n].
    //
    //      The (1/n) factor is domain.domain_inverse, applied as a scalar
    //      multiplication on the curve point.
    //
    //   4. Convert back to affine coordinates (g1::affine_element).
    //
    // =========================================================================

    // STEP 1: Copy affine points into projective working array.
    //
    // g1::affine_element uses (x, y) coordinates — compact but slow for
    // repeated additions. g1::element uses projective (x, y, z) coordinates
    // which allow faster point addition without modular inversions.
    // The ec_fft function requires projective (g1::element) inputs.
    //
    std::vector<g1::element> work(n);
    for (size_t i = 0; i < n; i++) {
        work[i] = g1::element(monomial_srs[i]);
    }

    // STEP 2: Apply forward EC-FFT.
    //
    // After this call, work[k] = [P(ω^k)]₁ for each k.
    // This evaluates the "polynomial" P(Y) at each n-th root of unity ω^k,
    // but entirely in the curve group — we never extract the secret x.
    //
    ec_fft(&work[0], domain);

    // STEP 3: Rearrange indices and scale by 1/n.
    //
    // For i = 0:   lagrange_srs[0] = (1/n) · work[(n-0) % n] = (1/n) · work[0]
    // For i = 1:   lagrange_srs[1] = (1/n) · work[n-1]
    // For i = 2:   lagrange_srs[2] = (1/n) · work[n-2]
    // ...
    // For i = n-1: lagrange_srs[n-1] = (1/n) · work[1]
    //
    // The scalar multiplication by domain.domain_inverse (= 1/n in the field)
    // scales each curve point. Converting the result to g1::affine_element
    // normalizes the projective coordinates back to affine (x, y) form.
    //
    for (size_t i = 0; i < n; i++) {
        size_t idx = (n - i) % n;
        g1::element scaled = work[idx] * domain.domain_inverse;
        lagrange_srs[i] = g1::affine_element(scaled);
    }
}

} // namespace g1_fft
} // namespace waffle