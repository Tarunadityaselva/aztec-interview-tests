import React, { useState } from 'react';
import ReactDOM from 'react-dom';
import { Colour } from './block';
import { BlockGrid } from './block_grid';
import styled, { createGlobalStyle } from 'styled-components';

const GlobalStyle = createGlobalStyle`
html, body, #root {
  background: grey;
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
}
`;

const StyledGrid = styled.div`
  width: 100%;
  height: 100%;
  background: grey;
`;

const StyledColumn = styled.div`
  float: left;
  background: grey;
  width: 10%;
  height: 100%;
`;

const StyledBlock = styled.div`
  width: 100%;
  height: 10%;
  margin: 0;
  padding: 0;
`;

function Blocky({ grid }: { grid: BlockGrid }) {
  // Counter state to force re-renders after grid mutations
  const [, setRenderCount] = useState(0);

  function handleClick(x: number, y: number) {
    grid.clicked(x, y);
    // Bump the counter so React re-renders with the updated grid
    setRenderCount(c => c + 1);
  }

  return (
    <StyledGrid>
      {grid.grid.map((col, i) => (
        <StyledColumn key={i}>
          {col.map((block, j) => (
            <StyledBlock
              key={j}
              style={{ background: block ? Colour[block.colour] : 'grey' }}
              onClick={() => handleClick(i, j)}
            ></StyledBlock>
          ))}
        </StyledColumn>
      ))}
    </StyledGrid>
  );
}

async function main() {
  const blockGrid = new BlockGrid(10, 10);
  console.log(blockGrid);
  ReactDOM.render(
    <>
      <GlobalStyle />
      <Blocky grid={blockGrid}></Blocky>
    </>,
    document.getElementById('root'),
  );
}

main().catch(console.error);
