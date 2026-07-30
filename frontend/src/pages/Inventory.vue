<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<h1 class="text-xl font-semibold text-ink-gray-9">Inventory</h1>

		<div class="mt-6 grid grid-cols-4 gap-4">
			<div v-for="stat in stats" :key="stat.label" class="rounded-lg border border-outline-gray-1 p-4">
				<div class="text-sm text-ink-gray-5">{{ stat.label }}</div>
				<div class="mt-1 truncate text-lg font-semibold text-ink-gray-9">{{ stat.value }}</div>
			</div>
		</div>

		<div class="mt-6 flex items-center justify-between gap-4">
			<FormControl
				v-model="search"
				type="text"
				placeholder="Search by item or product"
				class="w-64"
				:debounce="300"
			>
				<template #prefix><LucideSearch class="size-4 text-ink-gray-5" /></template>
			</FormControl>
			<Switch v-model="lowOnly" label="Low stock only" class="!w-auto" />
		</div>

		<CatalogListState
			:loading="inventory.loading && !inventory.data"
			:error="inventory.error"
			:empty="!rows.length"
			empty-title="No items found"
			empty-subtitle="Stock appears here once products are linked to items."
			@retry="inventory.reload()"
		/>

		<template v-if="rows.length && !inventory.error">
			<div class="mt-4 overflow-hidden rounded-lg border border-outline-gray-1">
				<table class="w-full text-base">
					<thead>
						<tr class="border-b border-outline-gray-1 text-left text-sm text-ink-gray-5">
							<th class="px-3 py-2 font-normal">Item code</th>
							<th class="px-3 py-2 font-normal">Label</th>
							<th class="px-3 py-2 font-normal">Product</th>
							<th class="px-3 py-2 text-right font-normal">Stock</th>
							<th class="px-3 py-2 text-right font-normal">Adjust</th>
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row in rows"
							:key="row.item_code"
							class="border-b border-outline-gray-1 last:border-b-0"
						>
							<td class="px-3 py-2 font-mono text-sm text-ink-gray-6">{{ row.item_code }}</td>
							<td class="px-3 py-2 font-medium text-ink-gray-8">{{ row.label }}</td>
							<td class="px-3 py-2">
								<router-link
									v-if="row.product"
									:to="{ path: '/products', query: { search: row.product_name } }"
									class="text-ink-gray-6 underline hover:text-ink-gray-8"
								>
									{{ row.product_name }}
								</router-link>
							</td>
							<td class="px-3 py-2 text-right">
								<Badge :theme="stockTheme(row)" size="sm">{{ row.stock }}</Badge>
							</td>
							<td class="px-3 py-2">
								<div class="flex items-center justify-end gap-2">
									<FormControl
										:model-value="drafts[row.item_code] ?? row.stock"
										type="number"
										class="w-24"
										@update:model-value="(value: string) => (drafts[row.item_code] = value)"
									/>
									<Button
										:disabled="!isChanged(row)"
										:loading="savingCode === row.item_code"
										@click="setStock(row)"
									>
										Set
									</Button>
								</div>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
			<CatalogPagination
				:start="start"
				:limit="PAGE_SIZE"
				:total="inventory.data?.total || 0"
				@update:start="start = $event"
			/>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Badge, FormControl, Switch, call, createResource, toast } from 'frappe-ui'

import LucideSearch from '~icons/lucide/search'

import CatalogListState from '@/components/CatalogListState.vue'
import CatalogPagination from '@/components/CatalogPagination.vue'

interface InventoryRow {
	item_code: string
	label: string
	product: string | null
	product_name: string | null
	stock: number
	low: boolean
}

const PAGE_SIZE = 20

const search = ref('')
const lowOnly = ref(false)
const start = ref(0)
const drafts = reactive<Record<string, string | number>>({})
const savingCode = ref('')

const inventory = createResource({
	url: 'shop.api.inventory.get_inventory',
	makeParams: () => ({
		search: search.value || undefined,
		low_only: lowOnly.value ? 1 : 0,
		start: start.value,
		limit: PAGE_SIZE,
	}),
	auto: true,
})

const rows = computed<InventoryRow[]>(() => inventory.data?.items || [])

const stats = computed(() => [
	{ label: 'Items tracked', value: inventory.data?.total ?? '--' },
	{ label: 'Low stock', value: inventory.data?.low_count ?? '--' },
	{ label: 'Low stock threshold', value: inventory.data?.threshold ?? '--' },
	{ label: 'Warehouse', value: inventory.data?.warehouse || '--' },
])

watch([search, lowOnly], () => {
	start.value = 0
	inventory.reload()
})
watch(start, () => inventory.reload())

function stockTheme(row: InventoryRow) {
	if (!row.stock) return 'red'
	if (row.low) return 'orange'
	return 'gray'
}

function isChanged(row: InventoryRow) {
	const draft = drafts[row.item_code]
	return draft !== undefined && draft !== '' && Number(draft) !== row.stock
}

async function setStock(row: InventoryRow) {
	const qty = Number(drafts[row.item_code])
	if (qty < 0) {
		toast.error('Stock cannot be negative')
		return
	}
	const previous = row.stock
	row.stock = qty
	savingCode.value = row.item_code
	try {
		const result = await call('shop.api.inventory.set_stock', { item_code: row.item_code, qty })
		row.stock = result.stock
		delete drafts[row.item_code]
		toast.success(`Stock set to ${result.stock}`)
	} catch (error) {
		row.stock = previous
		toast.error('Could not update stock')
	} finally {
		savingCode.value = ''
	}
}
</script>
