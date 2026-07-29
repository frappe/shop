<template>
	<div class="mx-auto max-w-4xl px-6 py-8">
		<h1 class="text-xl font-semibold text-ink-gray-9">Settings</h1>

		<div class="mt-6 max-w-md space-y-4">
			<FormControl v-model="form.store_name" label="Store name" />
			<div><FormControl v-model="form.enable_cod" type="checkbox" label="Enable cash on delivery" /></div>
			<div>
				<FormControl v-model="form.allow_out_of_stock" type="checkbox" label="Allow out of stock orders" />
			</div>
			<div><FormControl v-model="form.prices_include_tax" type="checkbox" label="Prices include tax" /></div>
			<div><Button variant="solid" :loading="settings.setValue.loading" @click="save">Save</Button></div>
		</div>

		<div class="mt-10">
			<h2 class="text-lg font-medium text-ink-gray-8">Theme</h2>
			<p class="mt-1 text-base text-ink-gray-6">
				Switching themes replaces your storefront pages. For visual edits, open
				<a href="/builder" target="_blank" class="underline hover:text-ink-gray-8">Builder</a>.
			</p>
			<div class="mt-4">
				<ThemeGrid :themes="themes.data || []" :applying-group="applyingGroup" @apply="applyTheme" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { FormControl, call, createDocumentResource, createResource, toast } from 'frappe-ui'

import ThemeGrid from '@/components/ThemeGrid.vue'

const applyingGroup = ref<string | null>(null)

const form = reactive({
	store_name: '',
	enable_cod: false,
	allow_out_of_stock: false,
	prices_include_tax: false,
})

const settings = createDocumentResource({
	doctype: 'Shop Settings',
	name: 'Shop Settings',
	auto: true,
})

watch(
	() => settings.doc,
	(doc) => {
		if (!doc) return
		form.store_name = doc.store_name || ''
		form.enable_cod = !!doc.enable_cod
		form.allow_out_of_stock = !!doc.allow_out_of_stock
		form.prices_include_tax = !!doc.prices_include_tax
	},
	{ immediate: true },
)

const themes = createResource({
	url: 'shop.themes.list_themes',
	auto: true,
})

async function save() {
	try {
		await settings.setValue.submit({
			store_name: form.store_name,
			enable_cod: form.enable_cod ? 1 : 0,
			allow_out_of_stock: form.allow_out_of_stock ? 1 : 0,
			prices_include_tax: form.prices_include_tax ? 1 : 0,
		})
		toast.success('Settings saved')
	} catch (error) {
		toast.error('Could not save settings')
	}
}

async function applyTheme(group: string) {
	applyingGroup.value = group
	try {
		await call('shop.themes.apply_theme', { group })
		toast.success('Theme applied')
		themes.reload()
	} catch (error) {
		toast.error('Could not apply theme')
	} finally {
		applyingGroup.value = null
	}
}
</script>
