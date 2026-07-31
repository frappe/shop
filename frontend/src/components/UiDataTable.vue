<template>
	<div class="overflow-hidden rounded-lg border border-outline-gray-1">
		<table class="w-full text-base">
			<thead>
				<tr class="border-b border-outline-gray-1 text-left text-sm text-ink-gray-5">
					<th
						v-for="column in columns"
						:key="column.key"
						class="px-3 py-2 font-normal"
						:class="{ 'text-right': column.align === 'right' }"
					>
						{{ column.label }}
					</th>
				</tr>
			</thead>
			<tbody v-if="loading">
				<tr v-for="i in 5" :key="i" class="border-b border-outline-gray-1 last:border-b-0">
					<td v-for="column in columns" :key="column.key" class="px-3 py-3">
						<div class="h-4 animate-pulse rounded bg-surface-gray-2" />
					</td>
				</tr>
			</tbody>
			<tbody v-else>
				<template v-for="row in rows" :key="rowId(row)">
					<tr
						class="border-b border-outline-gray-1 last:border-b-0"
						:class="{ 'cursor-pointer hover:bg-surface-gray-1': clickable }"
						@click="emit('row-click', row)"
					>
						<td
							v-for="column in columns"
							:key="column.key"
							class="px-3 py-2 text-ink-gray-7"
							:class="{ 'text-right': column.align === 'right' }"
						>
							<slot :name="`cell-${column.key}`" :row="row">
								{{ column.format ? column.format(row[column.key], row) : (row[column.key] ?? '-') }}
							</slot>
						</td>
					</tr>
					<tr v-if="expanded === rowId(row)">
						<td :colspan="columns.length" class="border-b border-outline-gray-1 bg-surface-gray-1 px-3 py-3">
							<slot name="expanded" :row="row" />
						</td>
					</tr>
				</template>
				<tr v-if="!rows.length">
					<td :colspan="columns.length">
						<slot name="empty" />
					</td>
				</tr>
			</tbody>
		</table>
	</div>
</template>

<script setup lang="ts">
export interface UiColumn {
	key: string
	label: string
	align?: 'left' | 'right'
	format?: (value: any, row: Record<string, any>) => string
}

export type UiRow = Record<string, any>

const props = defineProps<{
	columns: UiColumn[]
	rows: UiRow[]
	rowKey: string
	loading?: boolean
	clickable?: boolean
	expanded?: string | null
}>()

const emit = defineEmits<{ 'row-click': [row: UiRow] }>()

const rowId = (row: UiRow) => String(row[props.rowKey])
</script>
