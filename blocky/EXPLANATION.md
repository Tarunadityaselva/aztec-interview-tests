# Deep Dive: The Aztec Blocky Interview Question

## The Big Picture - What Is This?

This is a **front-end developer interview test** from Aztec Protocol. It's a classic "block-matching" puzzle game (think of simplified Candy Crush, or SameGame/Chain Shot). The game presents a **10x10 grid of randomly colored blocks**. When the user clicks on a block, all **connected blocks of the same color** are removed, and the blocks above them "fall down" due to gravity to fill the gaps.

The project gives you a working React app with the grid rendered and clickable — but the core game logic (`clicked`) is left as a stub for you to implement. You also need to write unit tests for your algorithm.

---

## File-by-File Breakdown

### 1. `src/block.ts` — The Block Data Model

```typescript
export enum Colour {
  RED,    // = 0
  GREEN,  // = 1
  BLUE,   // = 2
  ORANGE, // = 3
}

export class Block {
  public colour: Colour;

  constructor() {
    this.colour = Colour[Colour[Math.floor(Math.random() * (Colour.ORANGE + 1))] as keyof typeof Colour];
  }
}
```

**What it does:**

This file defines two things — the `Colour` enum and the `Block` class.

**The `Colour` enum:** TypeScript enums with no explicit values auto-assign integers starting at 0. So `RED = 0`, `GREEN = 1`, `BLUE = 2`, `ORANGE = 3`. This enum serves double duty in the project:
- As a numeric identifier for color comparisons (e.g., `block1.colour === block2.colour`)
- As a string lookup for CSS rendering (the React code does `Colour[block.colour]` which converts the numeric value back to the string name `"RED"`, `"GREEN"`, `"BLUE"`, or `"ORANGE"` — and CSS recognizes these as valid color names)

**The `Block` class:** Each block is a simple object with one property: `colour`. The constructor randomly assigns a color. The expression on line 12 is intentionally convoluted — let me break it down step by step:

1. `Colour.ORANGE + 1` evaluates to `3 + 1 = 4`
2. `Math.floor(Math.random() * 4)` gives a random integer: 0, 1, 2, or 3
3. `Colour[randomInt]` uses the reverse mapping of TypeScript numeric enums to get the string name (e.g., `Colour[2]` returns `"BLUE"`)
4. `as keyof typeof Colour` casts that string to a valid key of the Colour enum
5. `Colour["BLUE"]` maps back to the numeric value `2`

This round-trip (`number → string → number`) is unnecessarily complex. It's functionally equivalent to just writing:
```typescript
this.colour = Math.floor(Math.random() * 4);
```
The end result is the same: a random number between 0 and 3. This might be intentional interview flavor — testing if you can read unfamiliar code — or it might just be idiomatic caution to ensure the value is truly a valid member of the enum.

**Why this file matters:** Every cell in the grid holds a `Block`. Your algorithm needs to compare blocks by their `.colour` property to determine which blocks are "connected" (same color and adjacent).

---

### 2. `src/block_grid.ts` — The Core Game Logic (YOUR MAIN TASK)

```typescript
import { Block } from './block';

export class BlockGrid {
  public grid: Block[][] = [];

  constructor(public numCols: number, public numRows: number) {
    for (let x = 0; x < numCols; x++) {
      const col = [];
      for (let y = 0; y < numRows; y++) {
        col.push(new Block());
      }
      this.grid.push(col);
    }
  }

  clicked(x: number, y: number) {
    console.log(`(${x}, ${y}): Implement me...`);
  }
}
```

**This is the most critical file.** Let me dissect it in detail.

**The `grid` data structure:**

`grid` is typed as `Block[][]` — an array of arrays of Blocks. But the crucial detail is **how it's organized**: it's an array of **columns**, not rows.

```
grid[0] = column 0 = [Block(0,0), Block(0,1), Block(0,2), ..., Block(0,9)]
grid[1] = column 1 = [Block(1,0), Block(1,1), Block(1,2), ..., Block(1,9)]
...
grid[9] = column 9 = [Block(9,0), Block(9,1), Block(9,2), ..., Block(9,9)]
```

So `grid[x][y]` means **column x, row y**. This is a **column-major** layout. This is the opposite of what most people expect (most 2D arrays in textbooks are row-major where `array[row][col]`).

**Visual mapping:**

```
        col 0    col 1    col 2   ...  col 9
row 0   [0][0]   [1][0]   [2][0]       [9][0]   ← TOP of screen
row 1   [0][1]   [1][1]   [2][1]       [9][1]
row 2   [0][2]   [1][2]   [2][2]       [9][2]
...
row 9   [0][9]   [1][9]   [2][9]       [9][9]   ← BOTTOM of screen
```

**This column-major layout is architecturally important for the gravity mechanic.** When blocks are removed, the blocks above them in the **same column** need to fall down. Since each column is stored as a contiguous array, you can manipulate gravity by working within a single array — filter out the removed blocks, then pad the top with empty/null values (or new blocks, depending on design).

**The constructor:**

```typescript
constructor(public numCols: number, public numRows: number) {
```

Uses TypeScript's **parameter property** shorthand — `public numCols` both declares and assigns `this.numCols = numCols`. The constructor builds the grid by iterating: outer loop over columns (x), inner loop over rows (y), pushing a new randomly-colored Block into each position.

**The `clicked(x, y)` method — WHAT YOU MUST IMPLEMENT:**

This is the entire point of the interview. The stub currently just logs a message. You need to replace it with the full game algorithm. The method receives `x` (column index) and `y` (row index) of the clicked block.

**What `clicked` must do:**

1. **Identify the target block's color** at position `(x, y)`
2. **Find all connected blocks of the same color** using a graph traversal algorithm (flood fill)
3. **Remove those blocks** from the grid
4. **Apply gravity** — blocks above removed ones fall down to fill gaps
5. **(Implicitly) the UI must update** — since React renders from the grid data

---

### 3. `src/index.tsx` — The React Rendering Layer

```typescript
function Blocky({ grid }: { grid: BlockGrid }) {
  return (
    <StyledGrid>
      {grid.grid.map((col, i) => (
        <StyledColumn key={i}>
          {col.map((block, j) => (
            <StyledBlock
              key={j}
              style={{ background: Colour[block.colour] }}
              onClick={() => grid.clicked(i, j)}
            ></StyledBlock>
          ))}
        </StyledColumn>
      ))}
    </StyledGrid>
  );
}
```

**How rendering works:**

The `Blocky` component iterates over `grid.grid` (the column-major 2D array). For each column `i`, it creates a `StyledColumn` (a `<div>` floated left, 10% width, 100% height). Within each column, for each block at row `j`, it creates a `StyledBlock` (a `<div>` at 10% height).

**The color mapping:** `Colour[block.colour]` converts the numeric enum (e.g., `2`) back to the string name (`"BLUE"`). CSS recognizes `"RED"`, `"GREEN"`, `"BLUE"`, and `"ORANGE"` as valid color names, so the `background` style directly applies the color.

**The click handler:** `onClick={() => grid.clicked(i, j)}` passes the column index `i` and row index `j` to your game logic. This is where your implementation gets triggered.

**Layout architecture:**

```
[StyledGrid - 100% width, 100% height, grey background]
  [StyledColumn - float:left, 10% width, 100% height]  ← column 0
    [StyledBlock - 100% width, 10% height, colored]     ← row 0
    [StyledBlock - 100% width, 10% height, colored]     ← row 1
    ...
  [StyledColumn]  ← column 1
    ...
  ...10 columns total
```

Columns float left so they sit side-by-side. Each column takes 10% of the screen width (10 columns = 100%). Each block takes 10% of the column height (10 rows = 100%). This creates a perfect grid that fills the screen.

**The re-render problem:**

Notice that `main()` creates a `BlockGrid` once and renders it once with `ReactDOM.render()`. There is **no React state management** — no `useState`, no `setState`, no `forceUpdate`. This means **after you mutate the grid in `clicked()`, React won't know to re-render**.

This is a design challenge you need to solve. Options include:
- Calling `ReactDOM.render()` again after the click (brute force but works)
- Refactoring to use React state (`useState`) so mutations trigger re-renders
- Using a callback/event pattern

The current code gives `grid` as a prop to `Blocky`, but never re-renders. So your solution will likely need to address this.

---

### 4. `src/block_grid.test.ts` — The Unit Tests

```typescript
describe('BlockGrid', () => {
  it('should create blocks with one of the valid colours', () => {
    const blockGrid = new BlockGrid(10, 10);
    blockGrid.grid.forEach(col => {
      col.forEach(block => {
        expect(block).not.toBeNull();
        expect(block!.colour).toBeLessThanOrEqual(Colour.ORANGE);
      });
    });
  });

  it('should perform correct algorithm when clicked', () => {
    // Implement me.
  });
});
```

**Existing test:** The first test creates a 10x10 grid and verifies every block is non-null and has a valid colour (0-3). This tests the constructor and the `Block` class.

**What you must implement:** The second test is empty. You need to write tests for the `clicked()` algorithm. Good tests for this would:

- **Create a grid with known colors** (not random — you need to manually set block colors so you know exactly what should happen)
- **Test single-block click** — clicking a block that has no same-colored neighbors should remove only that one block
- **Test connected group removal** — set up a known cluster of same-colored blocks, click one, verify all connected ones are removed
- **Test that non-connected same-color blocks survive** — if there are two separate groups of blue, clicking one group shouldn't remove the other
- **Test gravity** — after removing blocks, verify that blocks above have "fallen down" to fill the gaps
- **Test edge cases** — clicking corners, clicking along edges, clicking a block that's part of a large group spanning the entire grid

---

## The Algorithm You Need to Implement

### Step 1: Flood Fill (Finding Connected Same-Color Blocks)

This is a classic **flood fill** problem, identical to the "paint bucket" tool in image editors, or the "find connected components" problem in graph theory.

Starting from the clicked position `(x, y)`, you need to find every block that:
1. Has the **same color** as `grid[x][y]`
2. Is **reachable** by moving only through **orthogonally adjacent** (up, down, left, right — NOT diagonal) blocks of that same color

**BFS approach (Breadth-First Search):**
```
1. Get the target color from grid[x][y]
2. Create a queue, add (x, y) to it
3. Create a "visited" set, add (x, y) to it
4. While the queue is not empty:
   a. Dequeue a position (cx, cy)
   b. Add (cx, cy) to the "to remove" list
   c. For each of the 4 neighbors (cx-1,cy), (cx+1,cy), (cx,cy-1), (cx,cy+1):
      - Skip if out of bounds
      - Skip if already visited
      - Skip if the block at that position is null/empty
      - Skip if the block's color != target color
      - Otherwise: mark as visited, enqueue it
5. Return the "to remove" list
```

**DFS approach (Depth-First Search):** Same logic but using a stack (or recursion) instead of a queue. Either approach works; BFS is often easier to reason about for this type of problem.

**Why orthogonal-only (not diagonal)?** This is the standard for block-matching games. The README's example images confirm this — only directly adjacent (sharing an edge) blocks count as "connected," not diagonally adjacent ones.

### Step 2: Remove the Blocks

Once you have the set of positions to remove, you need to clear those positions in the grid. There are two approaches:

**Approach A — Use `null` to represent empty cells:**
Change the grid type to `(Block | null)[][]` and set removed positions to `null`. This requires updating the rendering code to handle null blocks (render them as grey/empty).

**Approach B — Filter and pad:**
For each column, filter out the removed blocks, then pad the **beginning** of the array with new empty/null blocks so the array stays the same length. This naturally implements gravity in the same step.

### Step 3: Apply Gravity

After blocks are removed, remaining blocks above the gaps must "fall down." Since the grid is column-major, gravity operates **within each column independently**.

Consider column `[R, null, G, null, B]` (top to bottom, where null = removed):
- After gravity: `[null, null, R, G, B]`
- The colored blocks sink to the bottom, nulls bubble to the top.

**Implementation:** For each column:
1. Collect all non-null blocks (preserving their order)
2. Pad the front of the array with nulls until it reaches the original length
3. Replace the column in the grid

This is equivalent to: `column = [...nullPadding, ...survivingBlocks]`

### Step 4: Trigger Re-Render

As discussed, the current React code doesn't use state management. After mutating the grid, you need the UI to reflect the changes. The simplest approach given the existing architecture might be to re-render the entire app, or refactor `Blocky` to use React state.

---

## Key Gotchas and Edge Cases

1. **Column-major indexing:** `grid[x][y]` is column x, row y. Getting this wrong will cause bugs where horizontal operations affect vertical ones and vice versa.

2. **Row 0 is the TOP:** In the rendering code, `col.map((block, j) => ...)` iterates from index 0 downward. Index 0 is rendered first (at the top of the column). So when blocks "fall down," they move toward **higher indices** (toward `y = 9`).

3. **Clicking a single isolated block:** If you click a block that has no same-colored neighbors, it should still be removed (it's a connected component of size 1). Some game variants only remove groups of 2+, but the README doesn't specify this restriction.

4. **Null handling after removal:** Once blocks are removed and replaced with null, future clicks on empty cells need to be handled gracefully (no-op / early return).

5. **Re-rendering:** The most commonly overlooked part. The algorithm can be perfect, but if the UI doesn't update, the interviewer sees nothing.

6. **The grid is mutable:** The `grid` array and its contents are public and directly mutated. There's no immutability pattern here, which simplifies the algorithm but means you need to be careful about references.

---

## Summary Table

| File | Purpose | Status | What You Do |
|------|---------|--------|-------------|
| `block.ts` | Defines `Colour` enum and `Block` class | Complete | Read and understand |
| `block_grid.ts` | Grid data structure + game logic | **Incomplete** | **Implement `clicked()` method** |
| `block_grid.test.ts` | Unit tests | **Incomplete** | **Write tests for `clicked()`** |
| `index.tsx` | React UI rendering | Complete (but may need re-render fix) | May need minor changes for re-rendering and null-block handling |
| `index.html` | HTML entry point | Complete | No changes needed |
| `package.json` | Project config | Complete | No changes needed |

**In essence:** The interview tests three skills simultaneously:
1. **Algorithm design** — Can you implement flood fill / BFS / DFS?
2. **Data structure manipulation** — Can you handle the column-major grid, apply gravity, and manage null states?
3. **Front-end integration** — Can you make the React UI reflect the state changes?
