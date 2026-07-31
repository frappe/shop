<template>
	<div>
		<div v-if="loading" class="flex justify-center py-8">
			<LoadingIndicator class="size-5 text-ink-gray-5" />
		</div>

		<div v-else-if="error" class="flex flex-col items-center gap-2 py-8 text-center">
			<p class="text-sm text-ink-red-8">Could not load variants.</p>
			<Button @click="load">Try again</Button>
		</div>

		<template v-else-if="data">
			<template v-if="!data.has_variants">
				<div
					v-if="!data.can_add_options"
					class="rounded border border-outline-gray-1 bg-surface-gray-1 p-3 text-sm text-ink-gray-7"
				>
					<div class="font-medium text-ink-gray-8">Options cannot be added now</div>
					<p class="mt-1 text-ink-gray-6">
						This product already has stock or sales history, so its versions cannot be split into
						options. Create a new product with options instead.
					</p>
				</div>

				<template v-else-if="!editing">
					<div class="flex items-center justify-between gap-4 rounded border border-outline-gray-1 p-3">
						<div>
							<div class="text-sm font-medium text-ink-gray-8">This product has one version</div>
							<p class="mt-0.5 text-sm text-ink-gray-6">
								Add options like size or colour to sell more than one version.
							</p>
						</div>
						<Button @click="startEditing">Add options</Button>
					</div>
				</template>

				<template v-else>
					<CatalogOptionsEditor v-model="draftOptions" />
					<div class="mt-3 flex items-center gap-2">
						<Button variant="solid" :loading="saving" @click="saveOptions">Save options</Button>
						<Button @click="editing = false">Cancel</Button>
					</div>
				</template>
			</template>

			<template v-else>
				<div v-if="!editing" class="flex items-start justify-between gap-4">
					<div class="flex flex-wrap items-center gap-x-4 gap-y-1.5">
						<div v-for="option in data.options" :key="option.attribute" class="flex items-center gap-1.5">
							<span class="text-sm text-ink-gray-5">{{ option.attribute }}</span>
							<span
								v-for="value in option.values"
								:key="value"
								class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-sm text-ink-gray-7"
							>
								{{ value }}
							</span>
						</div>
					</div>
					<Button class="shrink-0" @click="startEditing">
						<template #prefix><LucidePencil class="size-4" /></template>
						Edit options
					</Button>
				</div>

				<template v-else>
					<CatalogOptionsEditor v-model="draftOptions" />
					<div class="mt-3 flex items-center gap-2">
						<Button variant="solid" :loading="saving" @click="saveOptions">Save options</Button>
						<Button @click="editing = false">Cancel</Button>
					</div>
				</template>

				<div
					v-if="data.missing_combinations"
					class="mt-3 flex items-center justify-between gap-4 rounded border border-outline-gray-1 bg-surface-gray-1 p-3"
				>
					<p class="text-sm text-ink-gray-7">
						{{ data.missing_combinations }}
						{{ data.missing_combinations === 1 ? 'combination is' : 'combinations are' }} not created yet.
					</p>
					<Button :loading="generating" @click="generateMissing">
						Generate {{ data.missing_combinations }} missing
						{{ data.missing_combinations === 1 ? 'combination' : 'combinations' }}
					</Button>
				</div>

				<div class="mt-3 overflow-hidden rounded border border-outline-gray-1">
					<table class="w-full text-sm">
						<thead>
							<tr class="border-b border-outline-gray-1 text-left text-ink-gray-5">
								<th class="w-12 px-3 py-1.5 font-normal">Image</th>
								<th class="px-3 py-1.5 font-normal">Variant</th>
								<th class="px-3 py-1.5 font-normal">Item code</th>
								<th class="px-3 py-1.5 font-normal">Price</th>
								<th class="px-3 py-1.5 font-normal">Stock</th>
								<th class="px-3 py-1.5 text-right font-normal">Available</th>
							</tr>
						</thead>
						<tbody>
							<tr
								v-for="variant in data.variants"
								:key="variant.item_code"
								class="border-b border-outline-gray-1 last:border-b-0"
							>
								<td class="px-3 py-1.5">
									<Tooltip text="Set variant image">
										<button
											class="flex size-9 items-center justify-center overflow-hidden rounded border border-outline-gray-1 hover:border-outline-gray-3"
											@click="editImage(variant)"
										>
											<img
												v-if="variant.image"
												:src="variant.image"
												alt=""
												class="size-full object-cover"
											/>
											<LucideImage v-else class="size-4 text-ink-gray-4" />
										</button>
									</Tooltip>
								</td>
								<td class="whitespace-nowrap px-3 py-1.5 font-medium text-ink-gray-8">
									{{ variantLabel(variant) }}
								</td>
								<td class="break-all px-3 py-1.5 font-mono text-ink-gray-5">{{ variant.item_code }}</td>
								<td class="px-3 py-1.5">
									<FormControl
										:model-value="priceDrafts[variant.item_code] ?? variant.price ?? 0"
										type="number"
										class="w-28"
										:disabled="savingCode === variant.item_code"
										@update:model-value="(value: string) => (priceDrafts[variant.item_code] = value)"
										@keydown.enter="savePrice(variant)"
										@blur="savePrice(variant)"
									/>
								</td>
								<td class="px-3 py-1.5">
									<div class="flex items-center gap-1.5">
										<FormControl
											:model-value="stockDrafts[variant.item_code] ?? variant.stock"
											type="number"
											class="w-24"
											:disabled="savingCode === variant.item_code"
											@update:model-value="(value: string) => (stockDrafts[variant.item_code] = value)"
											@keydown.enter="saveStock(variant)"
										/>
										<Button
											:disabled="!stockChanged(variant)"
											:loading="savingCode === variant.item_code"
											@click="saveStock(variant)"
										>
											Set
										</Button>
									</div>
								</td>
								<td class="px-3 py-1.5 text-right">
									<Switch
										:model-value="!variant.disabled"
										class="!w-auto"
										@update:model-value="(value: boolean) => setAvailability(variant, value)"
									/>
								</td>
							</tr>
						</tbody>
					</table>
				</div>

				<CatalogVariantImageDialog
					v-model="imageDialog"
					:gallery="gallery || []"
					:image="imageVariant?.image || null"
					@select="(url: string) => imageVariant && setImage(imageVariant, url)"
				/>
			</template>
		</template>
	</div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Button, FormControl, LoadingIndicator, Switch, Tooltip, call, dialog, toast } from 'frappe-ui'

import LucideImage from '~icons/lucide/image'
import LucidePencil from '~icons/lucide/pencil'

import CatalogOptionsEditor, { optionsError, type ProductOption } from '@/components/CatalogOptionsEditor.vue'
import CatalogVariantImageDialog from '@/components/CatalogVariantImageDialog.vue'

interface Variant {
	item_code: string
	item_name: string
	attributes: Record<string, string>
	price: number | null
	formatted_price: string | null
	stock: number
	disabled: number
	image: string | null
}

interface VariantsPayload {
	has_variants: boolean
	options: ProductOption[]
	variants: Variant[]
	missing_combinations?: number
	can_add_options?: boolean
}

const props = defineProps<{ product: string; gallery?: string[] }>()
const emit = defineEmits<{ updated: [boolean] }>()

const data = ref<VariantsPayload | null>(null)
const loading = ref(false)
const error = ref(false)
const editing = ref(false)
const saving = ref(false)
const generating = ref(false)
const savingCode = ref('')
const draftOptions = ref<ProductOption[]>([])
const imageDialog = ref(false)
const imageVariant = ref<Variant | null>(null)
const priceDrafts = reactive<Record<string, string | number>>({})
const stockDrafts = reactive<Record<string, string | number>>({})

watch(() => props.product, load, { immediate: true })

async function load() {
	loading.value = true
	error.value = false
	editing.value = false
	try {
		data.value = await call('shop.api.variants.get_variants', { product: props.product })
	} catch (err) {
		error.value = true
	} finally {
		loading.value = false
	}
}

function apply(payload: VariantsPayload) {
	data.value = payload
	emit('updated', payload.has_variants)
}

function variantLabel(variant: Variant) {
	const names = data.value?.options.map((option) => option.attribute) || []
	const ordered = names.map((name) => variant.attributes[name]).filter(Boolean)
	const values = ordered.length ? ordered : Object.values(variant.attributes)
	return values.join(' / ') || variant.item_name
}

function startEditing() {
	draftOptions.value = (data.value?.options || []).map((option) => ({
		attribute: option.attribute,
		values: [...option.values],
	}))
	if (!draftOptions.value.length) draftOptions.value = [{ attribute: '', values: [] }]
	editing.value = true
}

function saveOptions() {
	const message = optionsError(draftOptions.value)
	if (message) {
		toast.error(message)
		return
	}
	if (!data.value?.has_variants) {
		setOptions()
		return
	}
	dialog.confirm({
		title: 'Update options',
		message:
			'Existing variants are kept. Combinations that no longer match the options stay in the catalogue and must be removed manually.',
		confirmLabel: 'Update options',
		onConfirm: setOptions,
	})
}

async function setOptions() {
	saving.value = true
	try {
		apply(await call('shop.api.variants.set_options', { product: props.product, options: draftOptions.value }))
		editing.value = false
		toast.success('Options saved')
	} catch (err) {
		const messages = (err as { messages?: string[] }).messages
		toast.error(messages?.[0] || 'Could not save options')
	} finally {
		saving.value = false
	}
}

async function generateMissing() {
	generating.value = true
	try {
		apply(await call('shop.api.variants.generate', { product: props.product }))
		toast.success('Missing combinations created')
	} catch (err) {
		toast.error('Could not create the missing combinations')
	} finally {
		generating.value = false
	}
}

function stockChanged(variant: Variant) {
	const draft = stockDrafts[variant.item_code]
	return draft !== undefined && draft !== '' && Number(draft) !== variant.stock
}

async function savePrice(variant: Variant) {
	const draft = priceDrafts[variant.item_code]
	if (draft === undefined || draft === '' || Number(draft) === variant.price) return
	const price = Number(draft)
	if (price < 0) {
		toast.error('Price cannot be negative')
		return
	}
	const previous = variant.price
	variant.price = price
	await update(variant, { price }, `Price set to ${price}`, () => (variant.price = previous))
	delete priceDrafts[variant.item_code]
}

async function saveStock(variant: Variant) {
	if (!stockChanged(variant)) return
	const stock = Number(stockDrafts[variant.item_code])
	if (stock < 0) {
		toast.error('Stock cannot be negative')
		return
	}
	const previous = variant.stock
	variant.stock = stock
	await update(variant, { stock }, `Stock set to ${stock}`, () => (variant.stock = previous))
	delete stockDrafts[variant.item_code]
}

function editImage(variant: Variant) {
	imageVariant.value = variant
	imageDialog.value = true
}

async function setImage(variant: Variant, image: string) {
	const previous = variant.image
	variant.image = image || null
	await update(
		variant,
		{ image },
		image ? 'Variant image updated' : 'Variant image removed',
		() => (variant.image = previous),
	)
}

async function setAvailability(variant: Variant, available: boolean) {
	const previous = variant.disabled
	variant.disabled = available ? 0 : 1
	await update(
		variant,
		{ disabled: !available },
		available ? 'Variant is available' : 'Variant is hidden',
		() => (variant.disabled = previous),
	)
}

async function update(
	variant: Variant,
	changes: Record<string, unknown>,
	success: string,
	rollback: () => void,
) {
	savingCode.value = variant.item_code
	try {
		apply(await call('shop.api.variants.update_variant', { item_code: variant.item_code, ...changes }))
		toast.success(success)
	} catch (err) {
		rollback()
		toast.error('Could not update the variant')
	} finally {
		savingCode.value = ''
	}
}
</script>
