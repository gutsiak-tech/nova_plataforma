import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from '@tanstack/react-table'
import { useMemo, useState } from 'react'
import clsx from 'clsx'
import type { GoldRow } from '../../api/types'
import { EmptyState } from '../ui/EmptyState'
import { theme } from '../../lib/theme'

type Props = {
  columns: string[]
  rows: GoldRow[]
  maxHeightClass?: string
}

export function DataGrid({ columns, rows, maxHeightClass = 'max-h-[520px]' }: Props) {
  const [sorting, setSorting] = useState<SortingState>([])

  const defs = useMemo<ColumnDef<GoldRow>[]>(() => {
    return columns.map((c) => ({
      id: c,
      accessorKey: c,
      header: c,
      cell: (info) => {
        const v = info.getValue()
        if (v === null || v === undefined) {
          return <span className={theme.dataGrid.emptyCellClass}>—</span>
        }
        if (typeof v === 'number')
          return <span className="tabular-nums">{v.toLocaleString('pt-BR')}</span>
        return <span>{String(v)}</span>
      },
      sortingFn: (rowA, rowB, columnId) => {
        const a = rowA.getValue(columnId)
        const b = rowB.getValue(columnId)
        const na = typeof a === 'number' ? a : Number(a)
        const nb = typeof b === 'number' ? b : Number(b)
        if (!Number.isNaN(na) && !Number.isNaN(nb)) return na === nb ? 0 : na > nb ? 1 : -1
        return String(a ?? '').localeCompare(String(b ?? ''), 'pt-BR')
      },
    }))
  }, [columns])

  // TanStack Table exposes unstable function refs; React Compiler skips memoization by design.
  // eslint-disable-next-line react-hooks/incompatible-library -- useReactTable is the supported API
  const table = useReactTable({
    data: rows,
    columns: defs,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  if (!rows.length) {
    return (
      <EmptyState
        title="Tabela sem registros"
        description="Não há dados disponíveis para este recorte na competência selecionada."
      />
    )
  }

  return (
    <div className="space-y-2">
      <div className={clsx(theme.dataGrid.containerClass, maxHeightClass)}>
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className={theme.dataGrid.headerClass}>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className={theme.dataGrid.headerRowClass}>
                {hg.headers.map((h) => (
                  <th key={h.id} className={theme.dataGrid.headerCellClass}>
                    {h.isPlaceholder ? null : (
                      <button
                        type="button"
                        className={clsx(
                          theme.dataGrid.headerButtonClass,
                          h.column.getCanSort() && 'cursor-pointer select-none',
                        )}
                        onClick={h.column.getToggleSortingHandler()}
                      >
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        {h.column.getIsSorted() === 'asc' ? '↑' : null}
                        {h.column.getIsSorted() === 'desc' ? '↓' : null}
                      </button>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className={theme.dataGrid.bodyRowClass}>
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className={theme.dataGrid.bodyCellClass}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className={theme.dataGrid.footerClass}>
        {rows.length.toLocaleString('pt-BR')} registro(s) exibido(s)
        {rows.length >= 500 ? ' · limite da consulta pode truncar resultados' : ''}
      </p>
    </div>
  )
}
