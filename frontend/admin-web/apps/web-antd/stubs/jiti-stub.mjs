// Stub: jiti is a Node.js runtime TypeScript compiler.
// It's pulled into the browser bundle transitively but never actually
// called at runtime (all TS is pre-compiled by Vite).
// Provides just enough API surface to satisfy Rollup.

function jiti() {
  return jiti;
}
jiti.import = () => Promise.resolve({ default: {} });
jiti.resolve = () => '';
jiti.esmResolve = () => '';

export { jiti as createJiti };
export default jiti;
