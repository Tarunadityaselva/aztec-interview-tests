#pragma once

#include "hash_path.hpp"
#include "mock_db.hpp"
#include "sha256_hasher.hpp"
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

/**
 * The MerkleTree class implements a Merkle tree—a data structure that enables efficient
 * proofs of membership.
 */
class MerkleTree {
  private:
    static constexpr uint32_t MAX_DEPTH = 32;
    static constexpr uint32_t LEAF_BYTES = 64;
  public:
    /**
     * Constructs a new or existing tree.
     *
     * @param db The underlying database.
     * @param name The name of the tree.
     * @param depth The tree's depth (with leaves at layer = depth).
     * @param root (Optional) The pre-existing tree root.
     *
     * Throws std::runtime_error if depth is not in [1, 32].
     */
    MerkleTree(MockDB& db, const std::string& name, uint32_t depth, const sha256_hash_t& root = {})
        : db(db)
        , name(name)
        , depth(depth)
        , root(root)
        , hasher()
    {
        if (!(depth >= 1 && depth <= MAX_DEPTH)) {
            throw std::runtime_error("Bad depth");
        }

        // Pre-compute zero hashes for levels 0..depth.
        // Level 0: hash of a 64-byte zero leaf.
        // Level i: compress(zero[i-1], zero[i-1]).
        zero_hashes.resize(depth + 1);
        zero_hashes[0] = hasher.hash(std::vector<uint8_t>(LEAF_BYTES, 0));
        for (uint32_t i = 1; i <= depth; ++i) {
            zero_hashes[i] = hasher.compress(zero_hashes[i - 1], zero_hashes[i - 1]);
        }

        // Restore root from DB if present, otherwise use the computed empty root.
        auto stored = db.get(name);
        if (stored.has_value()) {
            this->root = stored.value();
        } else {
            this->root = zero_hashes[depth];
            db.put(name, this->root);
        }
    }

    /**
     * Creates (or restores) a MerkleTree instance.
     *
     * @param db The underlying database.
     * @param name The name of the tree.
     * @param depth The tree's depth (default is 32).
     * @return A MerkleTree instance.
     */
    static MerkleTree create(MockDB& db, const std::string& name, uint32_t depth = MAX_DEPTH)
    {
        return MerkleTree(db, name, depth);
    }

    /**
     * Returns the current Merkle tree root (32 bytes).
     */
    sha256_hash_t get_root() const
    {
        return root;
    }

    /**
     * Returns the hash path (Merkle proof) for a particular leaf index.
     *
     * At each level from 0 (leaf) to depth-1, we return the (left, right) pair
     * of hashes that contain the node on the path from leaf to root.
     *
     * @param index The leaf index.
     * @return A HashPath object.
     */
    HashPath get_hash_path(uint64_t index) const
    {
        std::vector<std::pair<sha256_hash_t, sha256_hash_t>> pairs;
        pairs.reserve(depth);

        for (uint32_t level = 0; level < depth; ++level) {
            uint64_t pos      = index >> level;
            uint64_t left_pos  = pos & ~uint64_t(1);  // round down to even
            uint64_t right_pos = pos | uint64_t(1);   // round up to odd

            sha256_hash_t left  = get_node(level, left_pos);
            sha256_hash_t right = get_node(level, right_pos);

            pairs.push_back({ left, right });
        }

        return HashPath(pairs);
    }

    /**
     * Updates the leaf at the given index with the specified 64-byte value.
     *
     * @param index The index of the leaf.
     * @param value A 64-byte vector representing the leaf data.
     * @return The new 32-byte tree root.
     *
     * Throws std::runtime_error if value is not exactly 64 bytes.
     */
    sha256_hash_t update_element(uint64_t index, const std::vector<uint8_t>& value)
    {
        if (value.size() != LEAF_BYTES) {
            throw std::runtime_error("Value must be exactly 64 bytes.");
        }

        std::vector<MockDBBatchItem> batch;

        // Hash the 64-byte leaf to produce the leaf node hash.
        sha256_hash_t current_hash = hasher.hash(value);
        uint64_t pos = index;

        for (uint32_t level = 0; level < depth; ++level) {
            // Persist this node.
            batch.push_back({ node_key(level, pos), current_hash });

            // Find the sibling (flip lowest bit).
            uint64_t sibling_pos = pos ^ uint64_t(1);
            sha256_hash_t sibling = get_node(level, sibling_pos);

            // Compute parent: left child has even position.
            if (pos % 2 == 0) {
                current_hash = hasher.compress(current_hash, sibling);
            } else {
                current_hash = hasher.compress(sibling, current_hash);
            }

            pos >>= 1;
        }

        root = current_hash;
        batch.push_back({ name, root });
        db.batch_write(batch);

        return root;
    }

  private:
    MockDB& db;
    std::string name;
    uint32_t depth;
    sha256_hash_t root;
    Sha256Hasher hasher;
    // zero_hashes[i] = the "empty" hash at level i.
    std::vector<sha256_hash_t> zero_hashes;

    // Builds the DB key for the node at (level, position).
    std::string node_key(uint32_t level, uint64_t pos) const
    {
        return name + ":" + std::to_string(level) + ":" + std::to_string(pos);
    }

    // Retrieves a node from the DB, or returns the zero hash for that level if absent.
    sha256_hash_t get_node(uint32_t level, uint64_t pos) const
    {
        auto stored = db.get(node_key(level, pos));
        if (stored.has_value()) {
            return stored.value();
        }
        return zero_hashes[level];
    }
};
