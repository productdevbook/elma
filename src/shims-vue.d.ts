// tsc doesn't understand .vue files on its own. This keeps imports typed as
// components without pulling in a separate checker binary.
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
