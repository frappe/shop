<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<UiPageHeader title="Dashboard">
			<template #actions>
				<TabButtons v-model="days" :options="periods" />
			</template>
		</UiPageHeader>

		<SetupGuide class="mt-6" />

		<div class="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
			<UiStatTile
				v-for="stat in stats"
				:key="stat.label"
				:label="stat.label"
				:value="stat.value"
				:hint="periodLabel"
			/>
		</div>

		<div class="mt-4 rounded-lg border border-outline-gray-1 p-4">
			<div class="flex items-baseline justify-between">
				<h2 class="text-base font-medium text-ink-gray-8">Revenue</h2>
				<span class="text-sm text-ink-gray-5">{{ periodLabel }}</span>
			</div>
			<UiSparkline class="mt-8" :series="series" />
		</div>

		<div class="mt-8">
			<h2 class="text-lg font-medium text-ink-gray-8">Needs attention</h2>
			<div class="mt-3 grid gap-4 sm:grid-cols-3">
				<router-link
					v-for="item in attention"
					:key="item.label"
					:to="item.route"
					class="group flex items-center gap-3 rounded-lg border border-outline-gray-1 p-4 transition hover:bg-surface-gray-1"
				>
					<component :is="item.icon" class="size-5 shrink-0 text-ink-gray-5" />
					<div class="flex-1">
						<div class="text-xl font-semibold text-ink-gray-9">{{ item.count }}</div>
						<div class="text-sm text-ink-gray-6">{{ item.label }}</div>
					</div>
					<LucideChevronRight class="size-4 text-ink-gray-4 transition group-hover:text-ink-gray-7" />
				</router-link>
			</div>
		</div>

		<div class="mt-8 grid gap-6 lg:grid-cols-3">
			<div class="lg:col-span-2">
				<h2 class="mb-3 text-lg font-medium text-ink-gray-8">Top products</h2>
				<UiDataTable
					:columns="productColumns"
					:rows="overview.data?.top_products || []"
					row-key="item_code"
					:loading="overview.loading"
				>
					<template #empty>
						<UiEmptyState
							:icon="LucidePackage"
							title="No sales yet"
							message="Top selling products will show up here."
						/>
					</template>
				</UiDataTable>
			</div>
			<div>
				<h2 class="mb-3 text-lg font-medium text-ink-gray-8">Order status</h2>
				<div class="rounded-lg border border-outline-gray-1 p-4">
					<div
						v-for="row in overview.data?.status_breakdown || []"
						:key="row.status"
						class="flex items-center justify-between py-1.5"
					>
						<UiStatusBadge :label="row.status" />
						<span class="text-base text-ink-gray-7">{{ row.count }}</span>
					</div>
					<div v-if="!overview.data?.status_breakdown?.length" class="py-2 text-p-sm text-ink-gray-5">
						No orders in this period
					</div>
				</div>
			</div>
		</div>

		<div class="mt-8">
			<div class="mb-3 flex items-center justify-between">
				<h2 class="text-lg font-medium text-ink-gray-8">Recent orders</h2>
				<router-link to="/orders" class="text-base text-ink-gray-6 hover:text-ink-gray-8">
					View all
				</router-link>
			</div>
			<UiDataTable
				:columns="orderColumns"
				:rows="recentOrders.data?.orders || []"
				row-key="name"
				:loading="recentOrders.loading"
				clickable
				@row-click="(row) => router.push(`/orders/${row.name}`)"
			>
				<template #cell-name="{ row }">
					<span class="font-medium text-ink-gray-8">{{ row.name }}</span>
				</template>
				<template #cell-status="{ row }">
					<UiStatusBadge :label="row.status" />
				</template>
				<template #cell-formatted_total="{ row }">
					<span class="text-ink-gray-8">{{ row.formatted_total }}</span>
				</template>
				<template #empty>
					<UiEmptyState
						:icon="LucideShoppingCart"
						title="No orders yet"
						message="Orders placed on your storefront will show up here."
					/>
				</template>
			</UiDataTable>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { TabButtons, createResource, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'

import LucideBoxes from '~icons/lucide/boxes'
import LucideChevronRight from '~icons/lucide/chevron-right'
import LucidePackage from '~icons/lucide/package'
import LucideShoppingBasket from '~icons/lucide/shopping-basket'
import LucideShoppingCart from '~icons/lucide/shopping-cart'

import SetupGuide from '@/components/SetupGuide.vue'
import UiDataTable from '@/components/UiDataTable.vue'
import UiEmptyState from '@/components/UiEmptyState.vue'
import UiPageHeader from '@/components/UiPageHeader.vue'
import UiSparkline from '@/components/UiSparkline.vue'
import UiStatTile from '@/components/UiStatTile.vue'
import UiStatusBadge from '@/components/UiStatusBadge.vue'

const router = useRouter()

const days = ref(30)
const periods = [
	{ label: '7 days', value: 7 },
	{ label: '30 days', value: 30 },
	{ label: '90 days', value: 90 },
]
const periodLabel = computed(() => `Last ${days.value} days`)

const overview = createResource({
	url: 'shop.api.analytics.get_overview',
	makeParams: () => ({ days: days.value }),
	auto: true,
	onError: () => toast.error('Could not load analytics'),
})
watch(days, () => overview.reload())

const dashboard = createResource({
	url: 'shop.api.admin.get_dashboard',
	auto: true,
	onError: () => toast.error('Could not load dashboard'),
})

const recentOrders = createResource({
	url: 'shop.api.orders.get_orders',
	params: { limit: 5 },
	auto: true,
	onError: () => toast.error('Could not load recent orders'),
})

const stats = computed(() => {
	const data = overview.data || {}
	return [
		{ label: 'Revenue', value: data.formatted_revenue ?? '-' },
		{ label: 'Orders', value: data.orders ?? '-' },
		{ label: 'Average order value', value: data.average_order_value ?? '-' },
		{ label: 'Conversion', value: data.conversion != null ? `${data.conversion}%` : '-' },
	]
})

const series = computed(() => overview.data?.series || [])

const attention = computed(() => {
	const data = dashboard.data || {}
	return [
		{
			label: 'orders to fulfill',
			count: data.pending_fulfillment ?? 0,
			route: '/orders',
			icon: LucidePackage,
		},
		{
			label: 'low stock products',
			count: data.low_stock ?? 0,
			route: '/inventory',
			icon: LucideBoxes,
		},
		{
			label: 'active carts',
			count: data.active_carts ?? 0,
			route: '/carts',
			icon: LucideShoppingBasket,
		},
	]
})

const productColumns = [
	{ key: 'item_name', label: 'Product' },
	{ key: 'qty', label: 'Units', align: 'right' as const },
	{ key: 'formatted_revenue', label: 'Revenue', align: 'right' as const },
]

const orderColumns = [
	{ key: 'name', label: 'Order' },
	{ key: 'customer_name', label: 'Customer' },
	{ key: 'transaction_date', label: 'Date' },
	{ key: 'status', label: 'Status' },
	{ key: 'formatted_total', label: 'Total', align: 'right' as const },
]
</script>
