// Minimal RFC 6901 JSON Pointer apply, mirroring st_vtt/patch.py.

export function splitPointer(path: string): string[] {
  if (path === '') return [];
  if (!path.startsWith('/')) throw new Error(`bad pointer ${path}`);
  return path.slice(1).split('/').map((p) => p.replace(/~1/g, '/').replace(/~0/g, '~'));
}

export function escapeToken(tok: string): string {
  return tok.replace(/~/g, '~0').replace(/\//g, '~1');
}

export function getPointer(doc: any, path: string): any {
  let node = doc;
  for (const tok of splitPointer(path)) {
    if (node == null) return undefined;
    node = node[tok];
  }
  return node;
}

export type PatchOp = 'set' | 'remove' | 'list_add' | 'list_remove' | 'text_patch';

export function applyPointer(doc: any, path: string, value: any, op: PatchOp = 'set'): void {
  if (op === 'list_add' || op === 'list_remove') {
    let list = getPointer(doc, path);
    if (!Array.isArray(list)) list = [];
    const next = op === 'list_add' ? (list.includes(value) ? list : [...list, value]) : list.filter((x: any) => x !== value);
    applyPointer(doc, path, next, 'set');
    return;
  }
  if (op === 'text_patch') op = 'set'; // caller passes the merged text as value
  const tokens = splitPointer(path);
  if (tokens.length === 0) {
    if (op === 'remove') throw new Error('cannot remove root');
    for (const k of Object.keys(doc)) delete doc[k];
    Object.assign(doc, value);
    return;
  }
  let node = doc;
  for (let i = 0; i < tokens.length - 1; i++) {
    const tok = tokens[i];
    const next = tokens[i + 1];
    if (Array.isArray(node)) {
      node = node[Number(tok)];
    } else {
      if (node[tok] == null) {
        if (op === 'remove') throw new Error(`missing ${tok}`);
        node[tok] = next === '-' || /^\d+$/.test(next) ? [] : {};
      }
      node = node[tok];
    }
    if (node == null) throw new Error(`cannot descend into ${tok}`);
  }
  const last = tokens[tokens.length - 1];
  if (Array.isArray(node)) {
    if (op === 'set') {
      if (last === '-' || Number(last) === node.length) node.push(value);
      else node[Number(last)] = value;
    } else {
      node.splice(Number(last), 1);
    }
  } else if (op === 'set') {
    node[last] = value;
  } else {
    delete node[last];
  }
}
