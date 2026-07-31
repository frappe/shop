<template>
	<div class="mx-auto max-w-5xl px-6 py-8">
		<UiPageHeader title="Customers" />

		<UiFilterBar v-model="search" search-placeholder="Search customers" class="mt-6">
			<template #trailing>{{ totalLabel }}</template>
		</UiFilterBar>

		<UiDataTable
			class="mt-4"
			:columns="columns"
			:rows="customers.data?.customers || []"
			row-key="name"
			:loading="customers.loading"
			clickable
			@row-click="(row) => router.push(`/customers/${row.name}`)"
		>
			<template #cell-customer_name="{ row }">
				<span class="font-medium text-ink-gray-8">{{ row.customer_name }}</span>
			</template>
			<template #empty>
				<UiEmptyState
					:icon="LucideUsers"
					title="No customers found"
					message="Customers are created automatically when orders come in."
				/>
			</template>
		</UiDataTable>

		<UiPagination v-model:start="start" class="mt-4" :limit="pageSize" :total="total" />
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { createResource, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'

import LucideUsers from '~icons/lucide/users'

import UiDataTable from '@/components/UiDataTable.vue'
import UiEmptyState from '@/components/UiEmptyState.vue'
import UiFilterBar from '@/components/UiFilterBar.vue'
import UiPageHeader from '@/components/UiPageHeader.vue'
import UiPagination from '@/components/UiPagination.vue'
import { formatDate } from '@/utils/format'

const pageSize = 20

const router = useRouter()
const search = ref('')
const start = ref(0)

const customers = createResource({
	url: 'shop.api.customers.get_customers',
	makeParams: () => ({
		search: search.value || undefined,
		start: start.value,
		limit: pageSize,
	}),
	auto: true,
	onError: () => toast.error('Could not load customers'),
})

watch(search, () => {
	start.value = 0
	customers.reload()
})
watch(start, () => customers.reload())

const total = computed(() => customers.data?.total || 0)
const totalLabel = computed(() => `${total.value} ${total.value === 1 ? 'customer' : 'customers'}`)

const columns = [
	{ key: 'customer_name', label: 'Customer' },
	{ key: 'email', label: 'Email' },
	{ key: 'orders', label: 'Orders', align: 'right' as const },
	{ key: 'formatted_spent', label: 'Spent', align: 'right' as const },
	{ key: 'last_order', label: 'Last order', format: formatDate },
	{ key: 'joined', label: 'Joined', format: formatDate },
]
</script>
