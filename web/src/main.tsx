import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Letter } from "./Letter";

const root = document.getElementById("root");
if (!root) {
  throw new Error("The page root is missing.");
}

createRoot(root).render(
  <StrictMode>
    <Letter />
  </StrictMode>,
);
