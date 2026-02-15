#include "indexed_merkle_tree.hpp"
#include <stdlib/merkle_tree/hash.hpp>

namespace plonk {
namespace stdlib {
namespace indexed_merkle_tree {

/**
 * Initialise an indexed merkle tree state with all the leaf values: H({0, 0, 0}).
 * Note that the leaf pre-image vector `leaves_` must be filled with {0, 0, 0} only at index 0.
 */
IndexedMerkleTree::IndexedMerkleTree(size_t depth)
    : depth_(depth)
{
    ASSERT(depth_ >= 1 && depth <= 32);
    total_size_ = 1UL << depth_;
    hashes_.resize(total_size_ * 2 - 2);

    // Initialise the leaf pre-image vector with a single zero leaf at index 0.
    leaf zero_leaf = { 0, 0, 0 };
    leaves_.push_back(zero_leaf);

    // Every leaf slot (occupied or not) hashes as H({0, 0, 0}).
    fr zero_hash = zero_leaf.hash();
    for (size_t i = 0; i < total_size_; i++) {
        hashes_[i] = zero_hash;
    }

    // Build the internal levels bottom-up.
    // Level 0 (leaves) occupies hashes_[0 .. total_size_-1].
    // Level 1 occupies hashes_[total_size_ .. total_size_ + total_size_/2 - 1], etc.
    size_t layer_size = total_size_;
    size_t offset = 0;
    while (layer_size > 2) {
        for (size_t i = 0; i < layer_size; i += 2) {
            hashes_[offset + layer_size + (i / 2)] = compress_pair(hashes_[offset + i], hashes_[offset + i + 1]);
        }
        offset += layer_size;
        layer_size >>= 1;
    }

    // The root is compress_pair of the last two entries in hashes_.
    root_ = compress_pair(hashes_[hashes_.size() - 2], hashes_[hashes_.size() - 1]);
}

/**
 * Fetches a hash-path from a given index in the tree.
 * Note that the size of the fr_hash_path vector should be equal to the depth of the tree.
 */
fr_hash_path IndexedMerkleTree::get_hash_path(size_t index)
{
    fr_hash_path path(depth_);

    // Walk from the leaf level upward, collecting sibling pairs at each level.
    size_t offset = 0;
    size_t layer_size = total_size_;
    for (size_t i = 0; i < depth_; i++) {
        // (index & ~1UL) gives the left sibling, (index | 1) gives the right sibling.
        path[i] = std::make_pair(hashes_[offset + (index & ~1UL)], hashes_[offset + (index | 1)]);
        offset += layer_size;
        layer_size >>= 1;
        index >>= 1;
    }

    return path;
}

/**
 * Update the node values (i.e. `hashes_`) given the leaf hash `value` and its index `index`.
 * Note that indexing in the tree starts from 0.
 * This function should return the updated root of the tree.
 */
fr IndexedMerkleTree::update_element_internal(size_t index, fr const& value)
{
    // Place the new leaf hash at level 0.
    size_t offset = 0;
    size_t layer_size = total_size_;
    hashes_[index] = value;

    // Propagate changes upward through every level until we reach the root.
    while (layer_size > 2) {
        // Compute the parent from the pair that `index` belongs to.
        fr left = hashes_[offset + (index & ~1UL)];
        fr right = hashes_[offset + (index | 1)];
        // Move to the next level: the parent is stored at offset + layer_size + index/2.
        index >>= 1;
        offset += layer_size;
        layer_size >>= 1;
        hashes_[offset + index] = compress_pair(left, right);
    }

    // The final pair produces the root.
    root_ = compress_pair(hashes_[offset], hashes_[offset + 1]);
    return root_;
}

/**
 * Insert a new `value` in a new leaf in the `leaves_` vector in the form: {value, nextIdx, nextVal}
 * You will need to compute `nextIdx, nextVal` according to the way indexed merkle trees work.
 * Further, you will need to update one old leaf pre-image on inserting a new leaf.
 * Lastly, insert the new leaf hash in the tree as well as update the existing leaf hash of the old leaf.
 */
fr IndexedMerkleTree::update_element(fr const& value)
{
    // 1. Duplicate check: if this value already exists in the tree, do nothing.
    for (size_t i = 0; i < leaves_.size(); i++) {
        if (leaves_[i].value == value) {
            return root_;
        }
    }

    // 2. Find the predecessor leaf — the existing leaf whose sorted-order range
    //    (leaf.value, leaf.nextValue) should contain the new value, or whose
    //    nextValue == 0 (meaning it's the current maximum and points to infinity).
    size_t predecessor_idx = 0;
    for (size_t i = 0; i < leaves_.size(); i++) {
        // A leaf is the predecessor if:
        //   - its value < the new value, AND
        //   - either its nextValue == 0 (it's the tail of the linked list), OR
        //     the new value < its nextValue (fits in the gap).
        if (uint256_t(leaves_[i].value) < uint256_t(value) &&
            (leaves_[i].nextValue == fr(0) || uint256_t(value) < uint256_t(leaves_[i].nextValue))) {
            predecessor_idx = i;
            break;
        }
    }

    // 3. Build the new leaf. It inherits the predecessor's old forward pointer.
    size_t new_leaf_idx = leaves_.size();
    leaf new_leaf = { value, leaves_[predecessor_idx].nextIndex, leaves_[predecessor_idx].nextValue };

    // 4. Update the predecessor to point to the new leaf.
    leaves_[predecessor_idx].nextIndex = index_t(new_leaf_idx);
    leaves_[predecessor_idx].nextValue = value;

    // 5. Append the new leaf to the pre-image vector.
    leaves_.push_back(new_leaf);

    // 6. Update hashes in the tree for both the modified predecessor and the new leaf.
    update_element_internal(predecessor_idx, leaves_[predecessor_idx].hash());
    update_element_internal(new_leaf_idx, new_leaf.hash());

    return root_;
}

} // namespace indexed_merkle_tree
} // namespace stdlib
} // namespace plonk