# Indexed Merkle Tree — Complete Technical Explanation

> A deep-dive into the interview exercise: the problem it solves, every file in the codebase,
> every function that was implemented, and the cryptographic intuition behind it all.

---

## Table of Contents

1. [Why Does This Data Structure Exist?](#1-why-does-this-data-structure-exist)
2. [Standard Merkle Trees — Quick Recap](#2-standard-merkle-trees--quick-recap)
3. [The Indexed Merkle Tree Idea](#3-the-indexed-merkle-tree-idea)
4. [File-by-File Breakdown](#4-file-by-file-breakdown)
   - [4.1 `leaf.hpp` — The Leaf Data Structure](#41-leafhpp--the-leaf-data-structure)
   - [4.2 `indexed_merkle_tree.hpp` — The Class Definition](#42-indexed_merkle_treehpp--the-class-definition)
   - [4.3 `indexed_merkle_tree.cpp` — The Implementation](#43-indexed_merkle_treecpp--the-implementation)
   - [4.4 `indexed_merkle_tree.test.cpp` — The Test Suite](#44-indexed_merkle_treetestcpp--the-test-suite)
5. [The `hashes_` Flat Array — Heart of the Tree](#5-the-hashes_-flat-array--heart-of-the-tree)
6. [Function-by-Function Deep Dive](#6-function-by-function-deep-dive)
   - [6.1 Constructor](#61-constructor--indexedmerkletreesize_t-depth)
   - [6.2 `get_hash_path`](#62-get_hash_path--merkle-proof-retrieval)
   - [6.3 `update_element_internal`](#63-update_element_internal--hash-propagation)
   - [6.4 `update_element`](#64-update_element--core-insertion-logic)
7. [Complete Walkthrough of the 5 State Transitions](#7-complete-walkthrough-of-the-5-state-transitions)
8. [Non-Membership Proofs — The Killer Feature](#8-non-membership-proofs--the-killer-feature)
9. [Bit-Manipulation Tricks Used](#9-bit-manipulation-tricks-used)
10. [Complexity Analysis](#10-complexity-analysis)

---

## 1. Why Does This Data Structure Exist?

A **standard Merkle tree** lets you prove that a value **is** a member of a set (a *membership proof*).
But it **cannot** efficiently prove that a value is **not** in the set. If someone asks
"prove that 25 is not in this tree," a standard Merkle tree has no mechanism for that — you would
have to reveal every single leaf.

An **Indexed Merkle tree** solves this. It augments each leaf with pointers that form a
**sorted linked list** threaded through the tree's leaves. Because the leaves are logically linked
in sorted order, you can prove non-membership by showing a single leaf whose range
`(value, nextValue)` contains the queried value — if the linked list has no gap where the value
could hide, it is provably not in the set.

**Real-world usage at Aztec:** This is critical in Aztec's privacy protocol for **nullifier trees**.
When a note (a private UTXO) is spent, its nullifier is added to the nullifier tree. Before
accepting a new transaction, the protocol must prove that the nullifier has *not* been spent before,
without revealing the entire set. The indexed Merkle tree makes this possible in zero knowledge.

---

## 2. Standard Merkle Trees — Quick Recap

A Merkle tree is a binary tree of hashes:

```
              root = H(A, B)
             /              \
        A = H(C, D)      B = H(E, F)
        /       \          /       \
   C = H(L0)  D = H(L1)  E = H(L2)  F = H(L3)
       |          |          |          |
      L0         L1         L2         L3
```

- **Leaves** store data (or hashes of data).
- **Internal nodes** store `H(left_child, right_child)`.
- The **root** is a single hash that commits to the entire dataset.
- A **Merkle proof** for leaf `L1` is `{C, B}` — the sibling hashes along the path to the root.
  A verifier computes `D = H(L1)`, then `A = H(C, D)`, then `root = H(A, B)` and checks it
  matches the known root.

**Limitation:** You can prove `L1` is in the tree, but you cannot prove that some value `X` is
*not* in the tree without revealing all leaves.

---

## 3. The Indexed Merkle Tree Idea

An indexed Merkle tree modifies the leaf structure. Instead of storing just a value, each leaf
stores three fields:

```
leaf = { value, nextIndex, nextValue }
```

| Field       | Type             | Meaning                                                    |
|-------------|------------------|------------------------------------------------------------|
| `value`     | Field element    | The actual value stored in this leaf                       |
| `nextIndex` | Integer          | The array index of the leaf with the next-higher value     |
| `nextValue` | Field element    | The value stored in that next leaf (redundantly stored)    |

**Invariant:** For every leaf, either:
- `nextValue > value` and no leaf in the tree has a value in the open interval `(value, nextValue)`, **or**
- `nextValue == 0`, meaning this leaf holds the largest value (points to "infinity").

This forms a **sorted linked list** threaded through array positions that are not necessarily
contiguous. The physical array order (index 0, 1, 2, ...) is the insertion order, while the
logical linked list order is the sorted value order.

**Why store `nextValue` redundantly?** In a zero-knowledge proof context, you need to prove that
no value exists between `value` and `nextValue`. Having `nextValue` directly in the leaf preimage
means the hash commits to this range, so a single Merkle proof proves both membership of `value`
*and* non-membership of anything in the open interval `(value, nextValue)`.

---

## 4. File-by-File Breakdown

### 4.1 `leaf.hpp` — The Leaf Data Structure

**Location:** `cryptography-engineer/src/indexed_merkle_tree/leaf.hpp`

This file defines the fundamental building block — the `leaf` struct.

```cpp
struct leaf {
    fr value;          // The stored value
    index_t nextIndex; // Index of the next-higher leaf
    fr nextValue;      // Value of the next-higher leaf

    // Hashing: Pedersen commitment to all three fields
    barretenberg::fr hash() const {
        return crypto::pedersen::compress_native({ value, nextIndex, nextValue });
    }
};
```

**Key methods:**

| Method | Purpose |
|--------|---------|
| `hash()` | Computes `Pedersen(value, nextIndex, nextValue)` — the leaf's commitment stored in the tree |
| `compress_pair(lhs, rhs)` | Computes `Pedersen(lhs, rhs)` — the internal node hash function |
| `operator==` | Default equality comparison for testing |
| `read()` / `write()` | Serialization to/from byte buffers |

**Why Pedersen hashing?** Pedersen hashes are algebraic — they can be efficiently verified inside
arithmetic circuits (SNARKs/PLONKs). This is essential because the tree operations must be
provable in zero knowledge.

**The "zero leaf"** `{0, 0, 0}` is special: it is the initial leaf at index 0. Its `nextIndex = 0`
and `nextValue = 0` means "there is no next element" (sentinel). Every unoccupied leaf slot also
hashes as `H({0, 0, 0})`.

---

### 4.2 `indexed_merkle_tree.hpp` — The Class Definition

**Location:** `cryptography-engineer/src/indexed_merkle_tree/indexed_merkle_tree.hpp`

This header defines the `IndexedMerkleTree` class and contains extensive ASCII art comments
showing the tree layout and all 5 state transitions.

#### Private Members

```cpp
size_t depth_;                         // Tree height (e.g., 3)
size_t total_size_;                    // Number of leaf slots = 2^depth_ (e.g., 8)
barretenberg::fr root_;                // Current Merkle root
std::vector<leaf> leaves_;             // Leaf preimages (grows dynamically)
std::vector<barretenberg::fr> hashes_; // ALL node hashes in the tree
```

**Critical distinction — `leaves_` vs `hashes_`:**

| Vector | Size | Contents |
|--------|------|----------|
| `leaves_` | Grows as values are inserted (starts at 1) | Preimages: `{value, nextIndex, nextValue}` structs |
| `hashes_` | Fixed at `2 * total_size_ - 2` | Hash commitments for ALL slots (including unoccupied) |

After inserting 4 values into a depth-3 tree: `leaves_.size() == 5` but `hashes_` always has 14 entries.

#### Public Interface

| Method | Purpose |
|--------|---------|
| `IndexedMerkleTree(depth)` | Constructor — build initial tree state |
| `get_hash_path(index)` | Return the Merkle proof (sibling hashes) for a leaf |
| `update_element_internal(index, value)` | Update a leaf hash and propagate up to root |
| `update_element(value)` | Insert a new value into the tree |
| `root()` | Return the current root hash |
| `get_hashes()` / `get_leaves()` | Read-only accessors for testing |

---

### 4.3 `indexed_merkle_tree.cpp` — The Implementation

**Location:** `cryptography-engineer/src/indexed_merkle_tree/indexed_merkle_tree.cpp`

This is where the four functions are implemented. See [Section 6](#6-function-by-function-deep-dive)
for the full deep-dive.

---

### 4.4 `indexed_merkle_tree.test.cpp` — The Test Suite

**Location:** `cryptography-engineer/src/indexed_merkle_tree/indexed_merkle_tree.test.cpp`

Contains two test cases and two helper functions.

#### Helper: `check_hash_path()`

Reconstructs the Merkle root from a leaf and its proof path:

```cpp
bool check_hash_path(const fr& root, const fr_hash_path& path,
                     const leaf& leaf_value, const size_t idx)
{
    auto current = leaf_value.hash();
    size_t index = idx;
    for (size_t i = 0; i < path.size(); ++i) {
        fr left  = (index & 1) ? path[i].first : current;
        fr right = (index & 1) ? current : path[i].second;
        current = compress_pair(left, right);
        index >>= 1;
    }
    return current == root;
}
```

At each level, if the current index is odd, the current hash is the right child; if even, it is
the left child. The verifier picks the appropriate sibling from the path and hashes them together.

#### Test 1: `test_toy_example`

A depth-3 tree (8 leaf slots) with a deterministic sequence:
1. Construct the tree, verify `leaves_.size() == 1`
2. Insert 30, verify leaves and linkage
3. Insert 10, verify leaves and linkage
4. Insert 20, verify leaves and linkage
5. Insert 20 again (duplicate), verify **nothing changes**
6. Insert 50, verify leaves and linkage
7. Manually compute the full tree, compare root and hash paths at indices 2, 3, 6, 7

#### Test 2: `test_real_example`

A depth-8 tree (256 leaf slots) with 20 random field elements:
1. Insert 20 random values
2. Pick a new random value not in the tree
3. Find the leaf whose range is closest to that value
4. Get the Merkle proof at that leaf's index
5. Verify the proof is valid — this proves non-membership

---

## 5. The `hashes_` Flat Array — Heart of the Tree

For a depth-3 tree with `total_size_ = 8`, the `hashes_` vector has `2 * 8 - 2 = 14` entries:

```
Index:   0    1    2    3    4    5    6    7    8    9   10   11   12   13
         |------------ Level 0 (leaves) ----------|  |--- Level 1 ---|  |Level 2|
         h₀₀  h₀₁  h₀₂  h₀₃  h₀₄  h₀₅  h₀₆  h₀₇  h₁₀  h₁₁  h₁₂  h₁₃  h₂₀  h₂₁
```

| Level | Start Offset | Count | What it stores |
|-------|-------------|-------|----------------|
| 0 (leaves) | `0` | `total_size_` = 8 | `H(leaf[i])` for each slot |
| 1 | `total_size_` = 8 | 4 | `compress_pair(h[2i], h[2i+1])` |
| 2 | `total_size_ + total_size_/2` = 12 | 2 | `compress_pair(h[8+2i], h[8+2i+1])` |
| root | Stored in `root_` (not in vector) | 1 | `compress_pair(h[12], h[13])` |

**Key arithmetic for navigating levels:**

For a node at index `j` within a level that starts at offset `o` and has `layer_size` nodes:
- **Left sibling:** `o + (j & ~1)` (clear last bit)
- **Right sibling:** `o + (j | 1)` (set last bit)
- **Parent:** lives at `o + layer_size + (j >> 1)` (next level, halved index)

---

## 6. Function-by-Function Deep Dive

### 6.1 Constructor — `IndexedMerkleTree(size_t depth)`

**Goal:** Build the initial tree where every leaf is `{0, 0, 0}`.

```cpp
IndexedMerkleTree::IndexedMerkleTree(size_t depth)
    : depth_(depth)
{
    ASSERT(depth_ >= 1 && depth <= 32);
    total_size_ = 1UL << depth_;
    hashes_.resize(total_size_ * 2 - 2);

    // Step 1: Seed the preimage store with a single zero leaf.
    leaf zero_leaf = { 0, 0, 0 };
    leaves_.push_back(zero_leaf);

    // Step 2: Fill all leaf slots with H({0, 0, 0}).
    fr zero_hash = zero_leaf.hash();
    for (size_t i = 0; i < total_size_; i++) {
        hashes_[i] = zero_hash;
    }

    // Step 3: Build internal levels bottom-up.
    size_t layer_size = total_size_;
    size_t offset = 0;
    while (layer_size > 2) {
        for (size_t i = 0; i < layer_size; i += 2) {
            hashes_[offset + layer_size + (i / 2)] =
                compress_pair(hashes_[offset + i], hashes_[offset + i + 1]);
        }
        offset += layer_size;
        layer_size >>= 1;
    }

    // Step 4: Compute root from the final two entries.
    root_ = compress_pair(hashes_[hashes_.size() - 2], hashes_[hashes_.size() - 1]);
}
```

**Why only one preimage in `leaves_`?** The test expects `leaves_.size() == 1` after construction.
Unoccupied slots are implicitly `{0, 0, 0}` — their hashes are already in `hashes_`, and their
preimages are only materialised when a value is actually inserted there.

**Iteration trace for depth 3:**

| Iteration | `layer_size` | `offset` | Reads pairs from | Writes to |
|-----------|-------------|----------|------------------|-----------|
| 1 | 8 | 0 | `hashes_[0..7]` | `hashes_[8..11]` (level 1) |
| 2 | 4 | 8 | `hashes_[8..11]` | `hashes_[12..13]` (level 2) |
| exit | 2 | 12 | — | — |

Since all leaves are identical, every node at each level is also identical — the initial tree is
perfectly symmetric.

---

### 6.2 `get_hash_path` — Merkle Proof Retrieval

**Goal:** Return the sibling pairs along the path from a leaf to the root.

```cpp
fr_hash_path IndexedMerkleTree::get_hash_path(size_t index)
{
    fr_hash_path path(depth_);

    size_t offset = 0;
    size_t layer_size = total_size_;
    for (size_t i = 0; i < depth_; i++) {
        path[i] = std::make_pair(
            hashes_[offset + (index & ~1UL)],  // left sibling
            hashes_[offset + (index | 1)]       // right sibling
        );
        offset += layer_size;
        layer_size >>= 1;
        index >>= 1;
    }

    return path;
}
```

**The return type** `fr_hash_path` is `std::vector<std::pair<fr, fr>>` with `depth_` entries.
Each entry `path[i]` is the `(left_child, right_child)` pair at level `i` on the path from the
queried leaf to the root.

**Trace for `get_hash_path(2)` in a depth-3 tree:**

| Level | `offset` | `index` | Left = `offset + (idx & ~1)` | Right = `offset + (idx \| 1)` | Result |
|-------|----------|---------|------------------------------|-------------------------------|--------|
| 0 | 0 | 2 | `hashes_[2]` | `hashes_[3]` | `(h₀₂, h₀₃)` |
| 1 | 8 | 1 | `hashes_[8]` | `hashes_[9]` | `(h₁₀, h₁₁)` |
| 2 | 12 | 0 | `hashes_[12]` | `hashes_[13]` | `(h₂₀, h₂₁)` |

This matches the test's expected path: `{(e010, e011), (e00, e01), (e0, e1)}`.

**Why indices 2 and 3 produce the same path:** They are siblings at level 0. Their parent is the
same node at level 1, so from level 1 upward the path is identical. At level 0, the pair is
`(hashes_[2], hashes_[3])` for both — because `2 & ~1 == 2` and `3 & ~1 == 2`, and `2 | 1 == 3`
and `3 | 1 == 3`.

---

### 6.3 `update_element_internal` — Hash Propagation

**Goal:** Given a new leaf hash and its index, update `hashes_` from the leaf level up to the root.

```cpp
fr IndexedMerkleTree::update_element_internal(size_t index, fr const& value)
{
    size_t offset = 0;
    size_t layer_size = total_size_;
    hashes_[index] = value;  // Store at leaf level

    // Walk upward, recomputing each parent.
    while (layer_size > 2) {
        fr left  = hashes_[offset + (index & ~1UL)];
        fr right = hashes_[offset + (index | 1)];
        index >>= 1;
        offset += layer_size;
        layer_size >>= 1;
        hashes_[offset + index] = compress_pair(left, right);
    }

    // Root from the final pair.
    root_ = compress_pair(hashes_[offset], hashes_[offset + 1]);
    return root_;
}
```

**Trace for `update_element_internal(2, new_hash)` in depth-3:**

| Step | `offset` | `layer_size` | `index` | Action |
|------|----------|-------------|---------|--------|
| init | 0 | 8 | 2 | `hashes_[2] = new_hash` |
| iter 1 | 0→8 | 8→4 | 2→1 | read `h[2], h[3]` → `h[9] = compress_pair(h[2], h[3])` |
| iter 2 | 8→12 | 4→2 | 1→0 | read `h[8], h[9]` → `h[12] = compress_pair(h[8], h[9])` |
| root | 12 | 2 | — | `root_ = compress_pair(h[12], h[13])` |

Only **O(depth)** nodes are recomputed — exactly those on the path from the leaf to the root.

---

### 6.4 `update_element` — Core Insertion Logic

**Goal:** Insert a new value into the tree, maintaining the sorted linked list invariant.

This is the most algorithmically complex function. It performs six steps:

```cpp
fr IndexedMerkleTree::update_element(fr const& value)
{
    // STEP 1: Duplicate check — if value exists, return immediately.
    for (size_t i = 0; i < leaves_.size(); i++) {
        if (leaves_[i].value == value) {
            return root_;
        }
    }

    // STEP 2: Find the predecessor leaf.
    size_t predecessor_idx = 0;
    for (size_t i = 0; i < leaves_.size(); i++) {
        if (uint256_t(leaves_[i].value) < uint256_t(value) &&
            (leaves_[i].nextValue == fr(0) ||
             uint256_t(value) < uint256_t(leaves_[i].nextValue))) {
            predecessor_idx = i;
            break;
        }
    }

    // STEP 3: Build the new leaf (inherits predecessor's old forward pointer).
    size_t new_leaf_idx = leaves_.size();
    leaf new_leaf = { value,
                      leaves_[predecessor_idx].nextIndex,
                      leaves_[predecessor_idx].nextValue };

    // STEP 4: Redirect predecessor to point to the new leaf.
    leaves_[predecessor_idx].nextIndex = index_t(new_leaf_idx);
    leaves_[predecessor_idx].nextValue = value;

    // STEP 5: Append the new leaf.
    leaves_.push_back(new_leaf);

    // STEP 6: Update tree hashes for both modified leaves.
    update_element_internal(predecessor_idx, leaves_[predecessor_idx].hash());
    update_element_internal(new_leaf_idx, new_leaf.hash());

    return root_;
}
```

#### Step-by-step explanation:

**Step 1 — Duplicate Check:**
Scan all existing leaves. If the value is already present, the operation is idempotent —
return the current root unchanged. This is tested when `update_element(20)` is called twice.

**Step 2 — Find the Predecessor:**
The predecessor is the existing leaf whose sorted-order range should contain the new value:
- `leaf.value < new_value` — the new value comes after this leaf in sorted order
- Either `leaf.nextValue == 0` (this is the largest value, pointing to infinity) or
  `new_value < leaf.nextValue` (the new value fits in the gap)

**Why `uint256_t` casts?** Field elements (`fr`) are modular arithmetic values. Direct `<`
comparison on `fr` may not give the expected integer ordering. Casting to `uint256_t`
ensures canonical integer comparison.

**Step 3 — Build New Leaf:**
The new leaf inherits the predecessor's old `{nextIndex, nextValue}`. This is a classic
**linked list splice**: if the sorted list was `... → predecessor → successor → ...`,
the new leaf takes over the link to the successor.

**Step 4 — Update Predecessor:**
The predecessor's forward pointer now points to the new leaf. After the splice:
`... → predecessor → NEW → successor → ...`

**Step 5 — Append:**
The new leaf is pushed to the end of `leaves_`. Its physical index is `leaves_.size() - 1`.

**Step 6 — Update Tree Hashes:**
Two `update_element_internal` calls:
1. The predecessor's hash changed (its `nextIndex`/`nextValue` are different).
2. The new leaf's hash must replace the zero hash at its position.

Both calls propagate from leaf to root, so the total work is `O(2 * depth)`.

---

## 7. Complete Walkthrough of the 5 State Transitions

### State 1 — Initial

```
leaves_ = [ {val:0, nextIdx:0, nextVal:0} ]

Sorted linked list: 0 → (end)

  index     0       1       2       3       4       5       6       7
  val       0       0       0       0       0       0       0       0
  nextIdx   0       0       0       0       0       0       0       0
  nextVal   0       0       0       0       0       0       0       0
```

Leaf 0 is the sentinel. `nextIdx=0, nextVal=0` means "no next element."

---

### State 2 — Insert value = 30

**Find predecessor:** Leaf 0 has `value=0 < 30` and `nextValue=0` (infinity). Match.

**New leaf (index 1):** `{30, 0, 0}` — inherits leaf 0's old pointer `{0, 0}` (no next).

**Update leaf 0:** `{0, 1, 30}` — now points to index 1.

```
leaves_ = [ {0, 1, 30}, {30, 0, 0} ]

Sorted linked list: 0 → 30 → (end)

  index     0       1       2       3       4       5       6       7
  val       0       30      0       0       0       0       0       0
  nextIdx   1       0       0       0       0       0       0       0
  nextVal   30      0       0       0       0       0       0       0
```

---

### State 3 — Insert value = 10

**Find predecessor:** Leaf 0 has `value=0 < 10` and `nextValue=30 > 10`. Range `(0, 30)` contains 10. Match.

**New leaf (index 2):** `{10, 1, 30}` — inherits leaf 0's old pointer `{1, 30}`.

**Update leaf 0:** `{0, 2, 10}` — now points to index 2.

```
leaves_ = [ {0, 2, 10}, {30, 0, 0}, {10, 1, 30} ]

Sorted linked list: 0 → 10 → 30 → (end)

  index     0       1       2       3       4       5       6       7
  val       0       30      10      0       0       0       0       0
  nextIdx   2       0       1       0       0       0       0       0
  nextVal   10      0       30      0       0       0       0       0
```

---

### State 4 — Insert value = 20

**Find predecessor:** Leaf 0 has range `(0, 10)` — does NOT contain 20. Leaf 1 has `value=30 > 20` — skip. Leaf 2 has `value=10 < 20` and `nextValue=30 > 20`. Range `(10, 30)` contains 20. Match.

**New leaf (index 3):** `{20, 1, 30}` — inherits leaf 2's old pointer `{1, 30}`.

**Update leaf 2:** `{10, 3, 20}` — now points to index 3.

```
leaves_ = [ {0, 2, 10}, {30, 0, 0}, {10, 3, 20}, {20, 1, 30} ]

Sorted linked list: 0 → 10 → 20 → 30 → (end)

  index     0       1       2       3       4       5       6       7
  val       0       30      10      20      0       0       0       0
  nextIdx   2       0       3       1       0       0       0       0
  nextVal   10      0       20      30      0       0       0       0
```

---

### State 4b — Insert value = 20 (duplicate)

**Duplicate check:** Leaf 3 has `value == 20`. Return immediately. Nothing changes.

---

### State 5 — Insert value = 50

**Find predecessor:** Leaf 0 has range `(0, 10)` — no. Leaf 1 has `value=30 < 50` and `nextValue=0` (infinity). Match.

**New leaf (index 4):** `{50, 0, 0}` — inherits leaf 1's old pointer `{0, 0}` (no next).

**Update leaf 1:** `{30, 4, 50}` — now points to index 4.

```
leaves_ = [ {0, 2, 10}, {30, 4, 50}, {10, 3, 20}, {20, 1, 30}, {50, 0, 0} ]

Sorted linked list: 0 → 10 → 20 → 30 → 50 → (end)

  index     0       1       2       3       4       5       6       7
  val       0       30      10      20      50      0       0       0
  nextIdx   2       4       3       1       0       0       0       0
  nextVal   10      50      20      30      0       0       0       0
```

---

## 8. Non-Membership Proofs — The Killer Feature

The second test (`test_real_example`) demonstrates the primary purpose of indexed Merkle trees.

To prove that value `x` is **not** in the tree:

1. Find the leaf where `leaf.value < x < leaf.nextValue`.
2. Produce a Merkle proof for that leaf.

The proof establishes three facts simultaneously:
1. **The leaf is in the tree** (standard Merkle proof verification).
2. **The leaf's preimage commits to the range** `(leaf.value, leaf.nextValue)` because the hash
   is `Pedersen(value, nextIndex, nextValue)`.
3. **No value exists in that range** by the indexed tree invariant — there are no leaves with
   values between `leaf.value` and `leaf.nextValue`.

Therefore, if `x` falls in this range, it is provably absent from the tree.

```
Example: Tree contains {0, 10, 20, 30, 50}

To prove 25 is NOT in the tree:
  → Leaf at index 3: {value: 20, nextIndex: 1, nextValue: 30}
  → 20 < 25 < 30, so 25 is in the gap
  → Merkle proof for leaf 3 proves this leaf is authentic
  → Therefore 25 is provably not in the tree
```

This is **impossible** with a standard Merkle tree and is why Aztec uses indexed Merkle trees
for nullifier sets.

---

## 9. Bit-Manipulation Tricks Used

Three bit operations appear throughout the implementation:

| Expression | Meaning | Example (index=5, binary `101`) |
|---|---|---|
| `index & ~1UL` | Clear last bit → left sibling | `5 & ~1 = 4` (binary `100`) |
| `index \| 1` | Set last bit → right sibling | `5 \| 1 = 5` (binary `101`) |
| `index >> 1` | Integer divide by 2 → parent index | `5 >> 1 = 2` (binary `10`) |

**Why these work:**
- In a binary tree, children at indices `2k` (left) and `2k+1` (right) share parent `k`.
- Clearing the last bit of any index gives the left child of its pair.
- Setting the last bit gives the right child of its pair.
- This is branch-free and works for both even and odd indices.

---

## 10. Complexity Analysis

| Operation | Time Complexity | Space Complexity |
|-----------|----------------|-----------------|
| Constructor | O(total_size_) = O(2^depth) | O(2^depth) for `hashes_` |
| `get_hash_path` | O(depth) | O(depth) for the returned path |
| `update_element_internal` | O(depth) | O(1) auxiliary |
| `update_element` | O(n + depth) where n = `leaves_.size()` | O(1) auxiliary |

The O(n) term in `update_element` comes from the linear scans for duplicate checking and
predecessor finding. For a production implementation, these could be optimised with a balanced
BST or hash set to O(log n) and O(1) respectively. However, the on-chain verification
(in a SNARK circuit) only needs to verify a single Merkle proof, which is O(depth).

---

*This explanation accompanies the implementation in `indexed_merkle_tree.cpp` on branch
`claude/indexed-merkle-tree-explanation-OuxoM`.*
