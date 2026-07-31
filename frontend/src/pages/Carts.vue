<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<UiPageHeader title="Carts" subtitle="Track open, abandoned, and converted shopper carts.">
			<template #actions>
				<div class="text-right">
					<div class="text-sm text-ink-gray-5">Open cart value</div>
					<div class="text-lg font-semibold text-ink-gray-9">{{ openValue }}</div>
				</div>
			</template>
		</UiPageHeader>

		<UiFilterBar class="mt-6">
			<TabButtons v-model="status" :options="statusTabs" />
			<template #trailing>{{ totalLabel }}</template>
		</UiFilterBar>

		<UiDataTable
			class="mt-4"
			:columns="columns"
			:rows="carts.data?.carts || []"
			row-key="name"
			:loading="carts.loading"
			clickable
			:expanded="expanded"
			@row-click="toggleRow"
		>
			<template #cell-shopper="{ row }">
				<span class="font-medium text-ink-gray-8">{{ row.shopper }}</span>
			</template>
			<template #cell-formatted_value="{ row }">
				<span class="text-ink-gray-8">{{ row.formatted_value }}</span>
			</template>
			<template #cell-sales_order="{ row }">
				<router-link
					v-if="row.sales_order"
					:to="`/orders/${row.sales_order}`"
					class="text-ink-gray-8 hover:underline"
					@click.stop
				>
					{{ row.sales_order }}
				</router-link>
				<span v-else>-</span>
			</template>
			<template #expanded="{ row }">
				<div v-if="row.items.length" class="max-w-md space-y-1">
					<div
						v-for="item in row.items"
						:key="item.item_code"
						class="flex items-center justify-between gap-8 text-sm text-ink-gray-7"
					>
						<span>{{ item.item_code }}</span>
						<span>{{ item.qty }} &times; {{ item.formatted_rate }}</span>
					</div>
				</div>
				<div v-else class="text-sm text-ink-gray-5">This cart is empty</div>
			</template>
			<template #empty>
				<UiEmptyState
					:icon="LucideShoppingBasket"
					:title="`No ${status.toLowerCase()} carts`"
					message="Carts show up here as shoppers browse your store."
				/>
			</template>
		</UiDataTable>

		<UiPagination v-model:start="start" class="mt-4" :limit="pageSize" :total="total" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TabButtons, createResource, toast } from 'frappe-ui'

import LucideShoppingBasket from '~icons/lucide/shopping-basket'

import UiDataTable from '@/components/UiDataTable.vue'
import UiEmptyState from '@/components/UiEmptyState.vue'
import UiFilterBar from '@/components/UiFilterBar.vue'
import UiPageHeader from '@/components/UiPageHeader.vue'
import UiPagination from '@/components/UiPagination.vue'
import { formatDateTime } from '@/utils/format'

const pageSize = 20

const status = ref('Active')
const statusTabs = [
	{ label: 'Active', value: 'Active' },
	{ label: 'Abandoned', value: 'Abandoned' },
	{ label: 'Converted', value: 'Converted' },
]

const start = ref(0)
const expanded = ref<string | null>(null)

const carts = createResource({
	url: 'shop.api.carts.get_carts',
	makeParams: () => ({ status: status.value, start: start.value, limit: pageSize }),
	auto: true,
	onError: () => toast.error('Could not load carts'),
})

watch(status, () => {
	start.value = 0
	expanded.value = null
	carts.reload()
})
watch(start, () => {
	expanded.value = null
	carts.reload()
})

const total = computed(() => carts.data?.total || 0)
const totalLabel = computed(() => `${total.value} ${total.value === 1 ? 'cart' : 'carts'}`)
const openValue = computed(() => carts.data?.open_value ?? '-')

function toggleRow(row: { name: string }) {
	expanded.value = expanded.value === row.name ? null : row.name
}

const columns = [
	{ key: 'shopper', label: 'Shopper' },
	{ key: 'item_count', label: 'Items', align: 'right' as const },
	{ key: 'formatted_value', label: 'Value', align: 'right' as const },
	{ key: 'last_active', label: 'Last active', format: formatDateTime },
	{ key: 'coupon_code', label: 'Coupon' },
	{ key: 'sales_order', label: 'Order' },
]
</script>
