import { LevelUp, LevelUpChain } from 'levelup';
import { HashPath } from './hash_path';
import { Sha256Hasher } from './sha256_hasher';

const MAX_DEPTH = 32;
const LEAF_BYTES = 64; // All leaf values are 64 bytes.

/**
 * The merkle tree, in summary, is a data structure with a number of indexable elements, and the property
 * that it is possible to provide a succinct proof (HashPath) that a given piece of data, exists at a certain index,
 * for a given merkle tree root.
 */
export class MerkleTree {
  private hasher = new Sha256Hasher();
  private root = Buffer.alloc(32);
  // zeroHashes[i] is the "empty" hash at level i.
  // Level 0 = leaf level: hash of a 64-byte zero buffer.
  // Level i = compress(zeroHashes[i-1], zeroHashes[i-1]).
  private zeroHashes: Buffer[] = [];

  /**
   * Constructs a new MerkleTree instance, either initializing an empty tree, or restoring pre-existing state values.
   * Use the async static `new` function to construct.
   *
   * @param db Underlying leveldb.
   * @param name Name of the tree, to be used when restoring/persisting state.
   * @param depth The depth of the tree, to be no greater than MAX_DEPTH.
   * @param root When restoring, you need to provide the root.
   */
  constructor(private db: LevelUp, private name: string, private depth: number, root?: Buffer) {
    if (!(depth >= 1 && depth <= MAX_DEPTH)) {
      throw Error('Bad depth');
    }

    // Pre-compute zero hashes for every level 0..depth.
    this.zeroHashes = this.computeZeroHashes(depth);

    if (root) {
      // Restoring an existing tree — use the provided root directly.
      this.root = root;
    } else {
      // Fresh tree — root is the zero hash at the top level.
      this.root = this.zeroHashes[depth];
    }
  }

  // Returns an array of length (depth+1) where index i is the "empty" hash at level i.
  private computeZeroHashes(depth: number): Buffer[] {
    const zeros: Buffer[] = new Array(depth + 1);
    zeros[0] = this.hasher.hash(Buffer.alloc(LEAF_BYTES));
    for (let i = 1; i <= depth; i++) {
      zeros[i] = this.hasher.compress(zeros[i - 1], zeros[i - 1]);
    }
    return zeros;
  }

  // Builds the DB key for a node at a given (level, position).
  private nodeKey(level: number, pos: number): string {
    return `${this.name}:${level}:${pos}`;
  }

  // Retrieves a node from the DB, falling back to the zero hash if absent.
  private async getNode(level: number, pos: number): Promise<Buffer> {
    const value: Buffer = await this.db.get(this.nodeKey(level, pos)).catch(() => null);
    return value || this.zeroHashes[level];
  }

  /**
   * Constructs or restores a new MerkleTree instance with the given `name` and `depth`.
   * The `db` contains the tree data.
   */
  static async new(db: LevelUp, name: string, depth = MAX_DEPTH) {
    const meta: Buffer = await db.get(Buffer.from(name)).catch(() => {});
    if (meta) {
      const root = meta.slice(0, 32);
      const depth = meta.readUInt32LE(32);
      return new MerkleTree(db, name, depth, root);
    } else {
      const tree = new MerkleTree(db, name, depth);
      await tree.writeMetaData();
      return tree;
    }
  }

  private async writeMetaData(batch?: LevelUpChain<string, Buffer>) {
    const data = Buffer.alloc(40);
    this.root.copy(data);
    data.writeUInt32LE(this.depth, 32);
    if (batch) {
      batch.put(this.name, data);
    } else {
      await this.db.put(this.name, data);
    }
  }

  getRoot() {
    return this.root;
  }

  /**
   * Returns the hash path for `index`.
   * e.g. To return the HashPath for index 2, return the nodes marked `*` at each layer.
   *     d0:                                            [ root ]
   *     d1:                      [*]                                               [*]
   *     d2:         [*]                      [*]                       [ ]                     [ ]
   *     d3:   [ ]         [ ]          [*]         [*]           [ ]         [ ]          [ ]        [ ]
   */
  async getHashPath(index: number) {
    const pairs: Buffer[][] = [];

    for (let level = 0; level < this.depth; level++) {
      // Position of the current node at this level.
      const pos = index >> level;
      // The pair is always (left_sibling, right_sibling) at the pair containing pos.
      const leftPos = pos & ~1;  // round down to nearest even
      const rightPos = pos | 1;  // round up to nearest odd

      const left = await this.getNode(level, leftPos);
      const right = await this.getNode(level, rightPos);

      pairs.push([left, right]);
    }

    return new HashPath(pairs);
  }

  /**
   * Updates the tree with `value` at `index`. Returns the new tree root.
   */
  async updateElement(index: number, value: Buffer) {
    const batch = this.db.batch();

    // Hash the 64-byte leaf value.
    let currentHash = this.hasher.hash(value);
    let pos = index;

    for (let level = 0; level < this.depth; level++) {
      // Persist this node.
      batch.put(this.nodeKey(level, pos), currentHash);

      // Find the sibling (flip lowest bit).
      const siblingPos = pos ^ 1;
      const sibling = await this.getNode(level, siblingPos);

      // Compute the parent: left child always has even position.
      if (pos % 2 === 0) {
        currentHash = this.hasher.compress(currentHash, sibling);
      } else {
        currentHash = this.hasher.compress(sibling, currentHash);
      }

      pos = pos >> 1;
    }

    this.root = currentHash;
    this.writeMetaData(batch);
    await batch.write();

    return this.root;
  }
}
