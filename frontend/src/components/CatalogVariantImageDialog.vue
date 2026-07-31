<template>
	<Dialog v-model="show" :options="{ title: 'Variant image', size: 'sm' }">
		<template #body-content>
			<template v-if="gallery.length">
				<p class="text-base text-ink-gray-6">Pick one of the product photos.</p>
				<div class="mt-3 grid grid-cols-4 gap-2">
					<button
						v-for="url in gallery"
						:key="url"
						class="overflow-hidden rounded border transition"
						:class="
							url === image
								? 'border-outline-gray-4 ring-1 ring-outline-gray-4'
								: 'border-outline-gray-1 hover:border-outline-gray-3'
						"
						@click="pick(url)"
					>
						<img :src="url" alt="" class="aspect-square w-full object-cover" />
					</button>
				</div>
			</template>
			<p v-else class="text-base text-ink-gray-6">
				This product has no photos yet. Upload one for this variant below.
			</p>
			<div class="mt-4 flex items-center gap-2">
				<FileUploader :file-types="['image/*']" @success="onUpload" @failure="onFailure">
					<template #default="{ uploading, progress, openFileSelector }">
						<Button :loading="uploading" @click="openFileSelector">
							<template #prefix><LucidePlus class="size-4" /></template>
							{{ uploading ? `Uploading ${progress}%` : 'Upload new image' }}
						</Button>
					</template>
				</FileUploader>
				<Button v-if="image" theme="red" @click="pick('')">
					<template #prefix><LucideTrash2 class="size-4" /></template>
					Remove image
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog, FileUploader, toast } from 'frappe-ui'

import LucidePlus from '~icons/lucide/plus'
import LucideTrash2 from '~icons/lucide/trash-2'

defineProps<{ gallery: string[]; image: string | null }>()
const emit = defineEmits<{ select: [string] }>()

const show = defineModel<boolean>({ required: true })

function pick(url: string) {
	emit('select', url)
	show.value = false
}

function onUpload(file: { file_url: string }) {
	pick(file.file_url)
}

function onFailure() {
	toast.error('Could not upload image')
}
</script>
