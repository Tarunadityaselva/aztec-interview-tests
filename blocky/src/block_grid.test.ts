import { Block, Colour } from './block';
import { BlockGrid } from './block_grid';

// Helper: create a small grid with specific colours so tests are deterministic.
// colours is a 2D array in visual layout: colours[row][col], top-to-bottom.
// We convert it to the column-major grid format used by BlockGrid.
function buildGrid(colours: Colour[][]): BlockGrid {
  const numRows = colours.length;
  const numCols = colours[0].length;
  const grid = new BlockGrid(numCols, numRows);

  for (let x = 0; x < numCols; x++) {
    for (let y = 0; y < numRows; y++) {
      const block = new Block();
      block.colour = colours[y][x]; // colours[row][col] -> grid[col][row]
      grid.grid[x][y] = block;
    }
  }
  return grid;
}

// Helper: read colours back out in visual row-major format (null for empty cells)
function readGrid(grid: BlockGrid): (Colour | null)[][] {
  const result: (Colour | null)[][] = [];
  for (let y = 0; y < grid.numRows; y++) {
    const row: (Colour | null)[] = [];
    for (let x = 0; x < grid.numCols; x++) {
      const block = grid.grid[x][y];
      row.push(block ? block.colour : null);
    }
    result.push(row);
  }
  return result;
}

const R = Colour.RED;
const G = Colour.GREEN;
const B = Colour.BLUE;
const O = Colour.ORANGE;

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

  it('should remove a single isolated block and apply gravity', () => {
    // 3x3 grid:
    //   R G B
    //   G B R
    //   B R G
    const grid = buildGrid([
      [R, G, B],
      [G, B, R],
      [B, R, G],
    ]);

    // Click the center block (x=1, y=1) which is BLUE, no blue neighbors
    grid.clicked(1, 1);

    // Blue at (1,1) removed. The G above it at (1,0) falls down.
    // Column 1 was [G, B, R] -> remove B -> [G, R] -> with gravity: [null, G, R]
    expect(readGrid(grid)).toEqual([
      [R, null, B],
      [G, G,    R],
      [B, R,    G],
    ]);
  });

  it('should remove a connected group of same-color blocks', () => {
    // 4x4 grid with a connected cluster of RED in the middle:
    //   G R R B
    //   B R R G
    //   G B B R
    //   R G B G
    const grid = buildGrid([
      [G, R, R, B],
      [B, R, R, G],
      [G, B, B, R],
      [R, G, B, G],
    ]);

    // Click (1,0) which is RED. Connected reds: (1,0),(2,0),(1,1),(2,1) — a 2x2 block
    grid.clicked(1, 0);

    // Columns 1 and 2 each lose 2 blocks, gravity fills top with null.
    // Col 0: unchanged [G, B, G, R]
    // Col 1: was [R, R, B, G] -> remove first two R -> [B, G] -> [null, null, B, G]
    // Col 2: was [R, R, B, B] -> remove first two R -> [B, B] -> [null, null, B, B]
    // Col 3: unchanged [B, G, R, G]
    expect(readGrid(grid)).toEqual([
      [G, null, null, B],
      [B, null, null, G],
      [G, B,    B,   R],
      [R, G,    B,   G],
    ]);
  });

  it('should not remove same-color blocks that are not connected', () => {
    // Two separate blue groups:
    //   B B R R
    //   R R R R
    //   R R B B
    //   R R R R
    const grid = buildGrid([
      [B, B, R, R],
      [R, R, R, R],
      [R, R, B, B],
      [R, R, R, R],
    ]);

    // Click top-left blue at (0,0). Connected blues: (0,0) and (1,0).
    // The bottom-right blues at (2,2) and (3,2) are NOT connected — they should survive.
    grid.clicked(0, 0);

    // Col 0: was [B, R, R, R] -> remove B at y=0 -> [R, R, R] -> [null, R, R, R]
    // Col 1: was [B, R, R, R] -> remove B at y=0 -> [R, R, R] -> [null, R, R, R]
    // Col 2 & 3: unchanged
    expect(readGrid(grid)).toEqual([
      [null, null, R, R],
      [R,    R,    R, R],
      [R,    R,    B, B],
      [R,    R,    R, R],
    ]);
  });

  it('should handle clicking on an already-empty cell', () => {
    const grid = buildGrid([
      [R, G],
      [B, R],
    ]);

    // Remove the R at (0,0)
    grid.clicked(0, 0);
    const afterFirst = readGrid(grid);

    // Now click the now-empty cell at (0,0)
    grid.clicked(0, 0);

    // Grid should not change
    expect(readGrid(grid)).toEqual(afterFirst);
  });

  it('should handle an L-shaped connected group', () => {
    //   R R G
    //   G R G
    //   G R R
    const grid = buildGrid([
      [R, R, G],
      [G, R, G],
      [G, R, R],
    ]);

    // Click (0,0) = RED. Connected: (0,0)->(1,0)->(1,1)->(1,2)->(2,2)
    // This is an L-shaped group of 5 reds.
    grid.clicked(0, 0);

    // Col 0: was [R, G, G] -> remove R at y=0 -> [G, G] -> [null, G, G]
    // Col 1: was [R, R, R] -> all removed -> [null, null, null]
    // Col 2: was [G, G, R] -> remove R at y=2 -> [G, G] -> [null, G, G]
    expect(readGrid(grid)).toEqual([
      [null, null, null],
      [G,    null, G],
      [G,    null, G],
    ]);
  });

  it('should apply gravity correctly with multiple gaps in a column', () => {
    // A column where removal creates multiple gaps:
    //   R
    //   B
    //   R
    //   B
    //   R
    const grid = buildGrid([
      [R],
      [B],
      [R],
      [B],
      [R],
    ]);

    // Click (0,0) = RED. Connected reds: (0,0), (0,2), (0,4) — but wait,
    // they are NOT connected because B blocks separate them.
    // Only (0,0) is removed.
    grid.clicked(0, 0);

    expect(readGrid(grid)).toEqual([
      [null],
      [B],
      [R],
      [B],
      [R],
    ]);
  });

  it('should remove all blocks when entire grid is one color', () => {
    const grid = buildGrid([
      [R, R, R],
      [R, R, R],
      [R, R, R],
    ]);

    grid.clicked(1, 1);

    // Every block is connected -> all removed
    expect(readGrid(grid)).toEqual([
      [null, null, null],
      [null, null, null],
      [null, null, null],
    ]);
  });
});
