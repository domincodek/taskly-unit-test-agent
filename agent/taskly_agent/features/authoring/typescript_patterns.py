import re

from .merge import Piece
from .paths import relative_import
from .typescript_pure import exported_functions


def pieces_for(root: object, source_path: str, source: str, test_text: str) -> list[Piece]:
    del root
    pieces = [
        *http_pieces(source_path, source),
        *hook_pieces(source_path, source),
        *provider_pieces(source_path, source, test_text),
        *component_pieces(source_path, source, test_text),
        *overdue_pieces(source_path, source, test_text),
    ]
    return [piece for piece in pieces if piece.name not in test_text]


def http_pieces(source_path: str, source: str) -> list[Piece]:
    if "fetch(" not in source or "response.ok" not in source or not source_path.endswith(".ts"):
        return []
    messages = re.findall(r"throw new Error\(\s*'([^']*)'", source, re.S)
    fallback_match = re.search(r"\?\s*body\.detail\s*:\s*'([^']*)'", source, re.S)
    if len(messages) < 2 or not fallback_match:
        return []
    network, validation = messages[0], messages[1]
    fallback = fallback_match.group(1)
    function = "request"
    found = re.search(r"export (?:async )?function (\w+)", source)
    if found:
        function = found.group(1)
    body = f"""
it('returns json from a successful response', async () => {{
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({{
      ok: true,
      status: 200,
      json: async () => ({{ status: 'ok' }}),
    }}),
  )
  await expect({function}('/health')).resolves.toEqual({{ status: 'ok' }})
  expect(fetch).toHaveBeenCalledWith('/api/health', {{
    headers: {{ 'Content-Type': 'application/json' }},
  }})
}})

it('returns undefined when the server has no content', async () => {{
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({{
      ok: true,
      status: 204,
      json: async () => {{
        throw new Error('no body')
      }},
    }}),
  )
  await expect({function}('/todos/1', {{ method: 'DELETE' }})).resolves.toBeUndefined()
}})

it('explains a validation error', async () => {{
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({{
      ok: false,
      status: 422,
      json: async () => ({{}}),
    }}),
  )
  await expect({function}('/todos', {{ method: 'POST' }})).rejects.toThrow(
    '{validation}',
  )
}})

it('uses a string error detail from the server', async () => {{
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({{
      ok: false,
      status: 400,
      json: async () => ({{ detail: 'Title is required.' }}),
    }}),
  )
  await expect({function}('/todos')).rejects.toThrow('Title is required.')
}})

it('falls back when the server sends an unexpected error', async () => {{
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({{
      ok: false,
      status: 500,
      json: async () => null,
    }}),
  )
  await expect({function}('/todos')).rejects.toThrow('{fallback}')
}})

it('reports that the server is unreachable', async () => {{
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network')))
  await expect({function}('/todos')).rejects.toThrow('{network}')
}})

it('preserves an aborted request', async () => {{
  const error = new DOMException('aborted', 'AbortError')
  const signal = AbortSignal.abort()
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
  await expect({function}('/todos', {{ signal }})).rejects.toBe(error)
}})
""".strip()
    body = "afterEach(() => vi.unstubAllGlobals())\n\n" + body
    return [
        Piece(
            "returns json from a successful response",
            body,
            (
                "import { afterEach, expect, it, vi } from 'vitest'",
                f"import {{ {function} }} from './{source_path.rsplit('/', 1)[-1].removesuffix('.ts')}'",
            ),
        )
    ]


def hook_pieces(source_path: str, source: str) -> list[Piece]:
    name_match = re.search(r"export function (\w+)", source)
    if not name_match or "/hooks/" not in source_path:
        return []
    name = name_match.group(1)
    fixture = relative_import(source_path, "frontend/src/test/todoFixture.ts")
    if "useIsMutating" in source:
        return [busy_piece(source_path, source, name)]
    if "useQuery" in source and "todosApi.list" in source:
        return [query_piece(source_path, source, name, fixture)]
    if "useMutation" in source and "todosApi.create" in source:
        return [create_piece(source_path, source, name, fixture)]
    if "useMutation" in source and "todosApi.update" in source:
        return [update_piece(source_path, source, name, fixture)]
    if "useMutation" in source and "todosApi.remove" in source:
        return [delete_piece(source_path, source, name, fixture)]
    if "useState" in source and "selectTodos" in source:
        return [filter_piece(source_path, name, fixture)]
    return []


def provider_pieces(source_path: str, source: str, test_text: str) -> list[Piece]:
    if "QueryClientProvider" not in source or "ThemeProvider" not in source or not source_path.endswith(".tsx"):
        return []
    match = re.search(r"export function (\w+)", source)
    if not match or match.group(1) in test_text:
        return []
    name = match.group(1)
    title = "renders children inside the application providers"
    body = f"""
it('{title}', () => {{
  const client = new QueryClient()
  render(
    <{name} client={{client}}>
      <p>Ready</p>
    </{name}>,
  )
  expect(screen.getByText('Ready')).toBeVisible()
}})
""".strip()
    return [
        Piece(
            title,
            body,
            (
                "import { QueryClient } from '@tanstack/react-query'",
                "import { render, screen } from '@testing-library/react'",
                "import { expect, it } from 'vitest'",
                f"import {{ {name} }} from './{name}'",
            ),
        )
    ]


def component_pieces(source_path: str, source: str, test_text: str) -> list[Piece]:
    if not source_path.endswith(".tsx"):
        return []
    match = re.search(r"export function (\w+)", source)
    if not match or match.group(1) in test_text:
        return []
    name = match.group(1)
    props_match = re.search(rf"export function {name}\(\s*\{{([^}}]*)\}}", source, re.S)
    type_match = re.search(r"\}\s*:\s*\{([^}]*)\}", source, re.S)
    if not props_match or not type_match:
        return []
    prop_names = [part.strip() for part in props_match.group(1).split(",") if part.strip()]
    types = {}
    for line in type_match.group(1).splitlines():
        cleaned = line.strip().rstrip(",")
        if ":" not in cleaned:
            continue
        prop, annotation = cleaned.split(":", 1)
        types[prop.strip()] = annotation.strip()
    if set(types) != set(prop_names):
        return []
    kinds = {prop: prop_kind(annotation) for prop, annotation in types.items()}
    if any(kind == "other" for kind in kinds.values()):
        return []
    compact = re.sub(r"\s+", " ", source)
    ternaries = re.findall(r"\{(\w+) \? '([^']*)' : '([^']*)'\}", compact)
    if not ternaries:
        return []
    condition = ternaries[0][0]
    if kinds.get(condition) != "boolean":
        return []
    true_strings = [item[1] for item in ternaries if item[0] == condition]
    false_strings = [item[2] for item in ternaries if item[0] == condition]
    callbacks = [prop for prop, kind in kinds.items() if kind == "callback"]
    button_when_false = f"!{condition}" in compact
    mock = ""
    imports = [
        "import { render, screen } from '@testing-library/react'",
        "import { expect, it, vi } from 'vitest'",
        f"import {{ {name} }} from './{name}'",
    ]
    barrel = re.search(r"from '([^']*design-system[^']*)'", source)
    if barrel and "/mocks" not in barrel.group(1):
        mock_path = relative_import(source_path, "frontend/src/design-system/mocks.tsx")
        mock = f"vi.mock('{barrel.group(1)}', () => import('{mock_path}'))\n\n"
    attrs_false = jsx_attrs(prop_names, kinds, {condition: "false"})
    attrs_true = jsx_attrs(prop_names, kinds, {condition: "true"})
    false_expects = "\n".join(
        f"  expect(screen.getAllByText('{text}').length).toBeGreaterThan(0)" for text in false_strings
    )
    true_expects = "\n".join(f"  expect(screen.getByText('{text}')).toBeVisible()" for text in true_strings)
    click = ""
    if callbacks and "onClick" in source:
        imports.insert(1, "import userEvent from '@testing-library/user-event'")
        callback = callbacks[0]
        click_attrs = jsx_attrs(prop_names, kinds, {condition: "false" if button_when_false else "true", callback: callback})
        click = f"""
it('forwards the requested action', async () => {{
  const user = userEvent.setup()
  const {callback} = vi.fn()
  render(<{name} {click_attrs} />)
  await user.click(screen.getByRole('button'))
  expect({callback}).toHaveBeenCalledTimes(1)
}})
"""
    disabled = ""
    if "disabled" in kinds and "disabled={" in source:
        disabled_attrs = jsx_attrs(
            prop_names,
            kinds,
            {"disabled": "true", condition: "false" if button_when_false else "true"},
        )
        disabled = f"""
it('blocks the action while the view is disabled', () => {{
  render(<{name} {disabled_attrs} />)
  expect(screen.getByRole('button')).toBeDisabled()
}})
"""
    hidden_button = ""
    if button_when_false:
        hidden_button = "\n  expect(screen.queryByRole('button')).not.toBeInTheDocument()"
    body = f"""{mock}it('shows the alternate copy', () => {{
  render(<{name} {attrs_false} />)
{false_expects}
}})

it('shows the matching copy', () => {{
  render(<{name} {attrs_true} />)
{true_expects}{hidden_button}
}})
{click}{disabled}""".strip()
    title = "shows the alternate copy"
    return [Piece(title, body, tuple(imports))]


def overdue_pieces(source_path: str, source: str, test_text: str) -> list[Piece]:
    for name, _params, body in exported_functions(source):
        if name in test_text:
            continue
        if "new Date()" in body and "due_date" in body and "completed" in body and "<" in body:
            fixture = relative_import(source_path, "frontend/src/test/todoFixture.ts")
            title = "marks an open task overdue only before the local day"
            test = f"""
it('{title}', () => {{
  vi.useFakeTimers()
  vi.setSystemTime(new Date(2026, 9, 8, 15, 0, 0))
  try {{
    const open = {{ ...todoFixture, due_date: '2026-10-07', completed: false }}
    expect({name}(open)).toBe(true)
    expect({name}({{ ...open, due_date: '2026-10-08' }})).toBe(false)
    expect({name}({{ ...open, due_date: null }})).toBe(false)
    expect({name}({{ ...open, completed: true }})).toBe(false)
  }} finally {{
    vi.useRealTimers()
  }}
}})
""".strip()
            return [
                Piece(
                    title,
                    test,
                    (
                        "import { expect, it, vi } from 'vitest'",
                        f"import {{ todoFixture }} from '{fixture}'",
                        f"import {{ {name} }} from './{source_path.rsplit('/', 1)[-1].removesuffix('.ts')}'",
                    ),
                )
            ]
    return []


def busy_piece(source_path: str, source: str, name: str) -> Piece:
    argument = "{ mutationKey: todoKeys.all }"
    found = re.search(r"useIsMutating\((\{.*?\})\)", source, re.S)
    if found:
        argument = re.sub(r"\s+", " ", found.group(1)).strip()
    keys = relative_import(source_path, "frontend/src/features/todos/api/queryKeys.ts")
    body = f"""
it('is busy only while a task mutation is running', () => {{
  vi.mocked(useIsMutating).mockReturnValue(0)
  expect(renderHook(() => {name}()).result.current).toBe(false)
  vi.mocked(useIsMutating).mockReturnValue(2)
  expect(renderHook(() => {name}()).result.current).toBe(true)
  expect(useIsMutating).toHaveBeenCalledWith({argument})
}})
""".strip()
    body = "vi.mock('@tanstack/react-query', () => ({ useIsMutating: vi.fn() }))\n\n" + body
    return Piece(
        "is busy only while a task mutation is running",
        body,
        (
            "import { useIsMutating } from '@tanstack/react-query'",
            "import { renderHook } from '@testing-library/react'",
            "import { expect, it, vi } from 'vitest'",
            f"import {{ todoKeys }} from '{keys}'",
            f"import {{ {name} }} from './{name}'",
        ),
    )


def query_piece(source_path: str, source: str, name: str, fixture: str) -> Piece:
    signal = "expect.any(AbortSignal)" if "signal" in source else "undefined"
    body = f"""
it('loads tasks through the task query', async () => {{
  vi.mocked(todosApi.list).mockResolvedValue([todoFixture])
  const client = new QueryClient({{
    defaultOptions: {{ queries: {{ retry: false }} }},
  }})
  const {{ result }} = renderHook(() => {name}(), {{
    wrapper: ({{ children }}: {{ children: ReactNode }}) =>
      createElement(QueryClientProvider, {{ client }}, children),
  }})
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(result.current.data).toEqual([todoFixture])
  expect(todosApi.list).toHaveBeenCalledWith({signal})
}})
""".strip()
    body = "vi.mock('../api/todos', () => ({ todosApi: { list: vi.fn() } }))\n\n" + body
    return Piece("loads tasks through the task query", body, _query_imports(source_path, name, fixture, "list"))


def create_piece(source_path: str, source: str, name: str, fixture: str) -> Piece:
    del source
    body = f"""
it('stores the created task ahead of the current list', async () => {{
  const saved = {{ ...todoFixture, id: 9, title: 'Created' }}
  vi.mocked(todosApi.create).mockResolvedValue(saved)
  const client = new QueryClient({{
    defaultOptions: {{ mutations: {{ retry: false }} }},
  }})
  client.setQueryData(todoKeys.list, [todoFixture])
  const {{ result }} = renderHook(() => {name}(), {{
    wrapper: ({{ children }}: {{ children: ReactNode }}) =>
      createElement(QueryClientProvider, {{ client }}, children),
  }})
  act(() => result.current.mutate(todoFixture))
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(todosApi.create).toHaveBeenCalledWith(todoFixture)
  expect(client.getQueryData(todoKeys.list)).toEqual([saved, todoFixture])
}})
""".strip()
    body = "vi.mock('../api/todos', () => ({ todosApi: { create: vi.fn() } }))\n\n" + body
    return Piece(
        "stores the created task ahead of the current list",
        body,
        _mutation_imports(source_path, name, fixture, "create"),
    )


def update_piece(source_path: str, source: str, name: str, fixture: str) -> Piece:
    del source
    body = f"""
it('replaces the updated task in the current list', async () => {{
  const saved = {{ ...todoFixture, title: 'Updated' }}
  vi.mocked(todosApi.update).mockResolvedValue(saved)
  const client = new QueryClient({{
    defaultOptions: {{ mutations: {{ retry: false }} }},
  }})
  client.setQueryData(todoKeys.list, [todoFixture])
  const {{ result }} = renderHook(() => {name}(), {{
    wrapper: ({{ children }}: {{ children: ReactNode }}) =>
      createElement(QueryClientProvider, {{ client }}, children),
  }})
  act(() => result.current.mutate({{ id: todoFixture.id, input: {{ title: 'Updated' }} }}))
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(todosApi.update).toHaveBeenCalledWith(todoFixture.id, {{ title: 'Updated' }})
  expect(client.getQueryData(todoKeys.list)).toEqual([saved])
}})
""".strip()
    body = "vi.mock('../api/todos', () => ({ todosApi: { update: vi.fn() } }))\n\n" + body
    return Piece(
        "replaces the updated task in the current list",
        body,
        _mutation_imports(source_path, name, fixture, "update"),
    )


def delete_piece(source_path: str, source: str, name: str, fixture: str) -> Piece:
    del source
    body = f"""
it('removes the deleted task from the current list', async () => {{
  const other = {{ ...todoFixture, id: 8 }}
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  const client = new QueryClient({{
    defaultOptions: {{ mutations: {{ retry: false }} }},
  }})
  client.setQueryData(todoKeys.list, [todoFixture, other])
  const {{ result }} = renderHook(() => {name}(), {{
    wrapper: ({{ children }}: {{ children: ReactNode }}) =>
      createElement(QueryClientProvider, {{ client }}, children),
  }})
  act(() => result.current.mutate(todoFixture.id))
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(todosApi.remove).toHaveBeenCalledWith(todoFixture.id)
  expect(client.getQueryData(todoKeys.list)).toEqual([other])
}})
""".strip()
    body = "vi.mock('../api/todos', () => ({ todosApi: { remove: vi.fn() } }))\n\n" + body
    return Piece(
        "removes the deleted task from the current list",
        body,
        _mutation_imports(source_path, name, fixture, "remove"),
    )


def filter_piece(source_path: str, name: str, fixture: str) -> Piece:
    body = f"""
it('starts from the default view and applies the status filter', () => {{
  const {{ result }} = renderHook(() => {name}([todoFixture]))
  expect(result.current.filter).toBe('all')
  expect(result.current.search).toBe('')
  expect(result.current.sort).toBe('newest')
  expect(result.current.visible).toEqual([todoFixture])
  act(() => result.current.setFilter('completed'))
  expect(result.current.filter).toBe('completed')
  expect(result.current.visible).toEqual([])
  act(() => result.current.setSearch('missing-task'))
  expect(result.current.search).toBe('missing-task')
}})
""".strip()
    return Piece(
        "starts from the default view and applies the status filter",
        body,
        (
            "import { act, renderHook } from '@testing-library/react'",
            "import { expect, it } from 'vitest'",
            f"import {{ todoFixture }} from '{fixture}'",
            f"import {{ {name} }} from './{PathName(source_path)}'",
        ),
    )


def _query_imports(source_path: str, name: str, fixture: str, method: str) -> tuple[str, ...]:
    return (
        "import { QueryClient, QueryClientProvider } from '@tanstack/react-query'",
        "import { renderHook, waitFor } from '@testing-library/react'",
        "import { createElement, type ReactNode } from 'react'",
        "import { expect, it, vi } from 'vitest'",
        f"import {{ todoFixture }} from '{fixture}'",
        "import { todosApi } from '../api/todos'",
        f"import {{ {name} }} from './{name}'",
    )


def _mutation_imports(source_path: str, name: str, fixture: str, method: str) -> tuple[str, ...]:
    keys = relative_import(source_path, "frontend/src/features/todos/api/queryKeys.ts")
    return (
        "import { QueryClient, QueryClientProvider } from '@tanstack/react-query'",
        "import { act, renderHook, waitFor } from '@testing-library/react'",
        "import { createElement, type ReactNode } from 'react'",
        "import { expect, it, vi } from 'vitest'",
        f"import {{ todoFixture }} from '{fixture}'",
        f"import {{ todoKeys }} from '{keys}'",
        "import { todosApi } from '../api/todos'",
        f"import {{ {name} }} from './{name}'",
    )


def prop_kind(annotation: str) -> str:
    compact = annotation.replace(" ", "")
    if compact == "boolean":
        return "boolean"
    if compact in {"()=>void", "()=>undefined"}:
        return "callback"
    return "other"


def jsx_attrs(prop_names: list[str], kinds: dict[str, str], overrides: dict[str, str]) -> str:
    parts = []
    for prop in prop_names:
        if prop in overrides and kinds[prop] == "boolean":
            value = overrides[prop]
            parts.append(f"{prop}" if value == "true" else f"{prop}={{false}}")
            continue
        if prop in overrides and kinds[prop] == "callback":
            parts.append(f"{prop}={{{overrides[prop]}}}")
            continue
        if kinds[prop] == "boolean":
            parts.append(f"{prop}={{false}}")
        else:
            parts.append(f"{prop}={{vi.fn()}}")
    return " ".join(parts)


def PathName(source_path: str) -> str:
    return source_path.rsplit("/", 1)[-1].removesuffix(".ts").removesuffix(".tsx")
