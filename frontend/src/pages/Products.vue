<template>
	<div class="mx-auto max-w-4xl px-6 py-8">
		<div class="flex items-center justify-between">
			<h1 class="text-xl font-semibold text-ink-gray-9">Products</h1>
			<Button variant="solid" @click="openNew">New product</Button>
		</div>

		<div class="mt-6 overflow-hidden rounded-lg border border-outline-gray-1">
			<table class="w-full text-base">
				<thead>
					<tr class="border-b border-outline-gray-1 text-left text-sm text-ink-gray-5">
						<th class="px-3 py-2 font-normal">Product</th>
						<th class="px-3 py-2 font-normal">Slug</th>
						<th class="px-3 py-2 text-right font-normal">Ranking</th>
						<th class="px-3 py-2 text-right font-normal">Published</th>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="row in products.data || []"
						:key="row.name"
						class="cursor-pointer border-b border-outline-gray-1 last:border-b-0 hover:bg-surface-gray-1"
						@click="openEdit(row.name)"
					>
						<td class="px-3 py-2 font-medium text-ink-gray-8">{{ row.product_name }}</td>
						<td class="px-3 py-2 text-ink-gray-6">{{ row.slug }}</td>
						<td class="px-3 py-2 text-right text-ink-gray-6">{{ row.ranking }}</td>
						<td class="px-3 py-2 text-right" @click.stop>
							<Switch
								:model-value="!!row.published"
								@update:model-value="(value: boolean) => togglePublished(row.name, value)"
							/>
						</td>
					</tr>
					<tr v-if="!(products.data || []).length">
						<td colspan="4" class="px-3 py-8 text-center text-ink-gray-5">No products yet</td>
					</tr>
				</tbody>
			</table>
		</div>

		<ProductDialog v-model="showDialog" :edit-name="editName" :list="products" />
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Switch, createListResource } from 'frappe-ui'

import ProductDialog from '@/components/ProductDialog.vue'

const showDialog = ref(false)
const editName = ref<string | null>(null)

const products = createListResource({
	doctype: 'Shop Product',
	fields: ['name', 'product_name', 'slug', 'published', 'ranking'],
	orderBy: 'ranking desc',
	pageLength: 100,
	auto: true,
})

function openNew() {
	editName.value = null
	showDialog.value = true
}

function openEdit(name: string) {
	editName.value = name
	showDialog.value = true
}

function togglePublished(name: string, value: boolean) {
	products.setValue.submit({ name, published: value ? 1 : 0 })
}
</script>
