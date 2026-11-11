/**
 * create-product.js
 * Quản lý tương tác client-side, Variation Matrix, Media Gallery, Category & Author pickers,
 * và kiểm soát Single Source of Truth validation cho trang Tạo sản phẩm mới WRYDECO.
 */

// ==========================================
// 1. GLOBAL STATE
// ==========================================
const state = {
    currentStoreType: typeof CURRENT_STORE_TYPE !== 'undefined' ? CURRENT_STORE_TYPE : 'custom',
    authors: [],
    media: [], // [{ id, kind: 'url'|'device', url, file, previewUrl, position }]
    tags: [],
    selectedCategoryId: '',
    selectedCategoryName: '',
    selectedAuthorId: '',
    selectedAuthorData: null,
    
    // Variation State
    options: [
        {
            clientId: 'opt_' + Math.random().toString(36).substr(2, 9),
            name: 'Color',
            isEditing: true,
            values: [
                { clientId: 'val_' + Math.random().toString(36).substr(2, 9), label: 'Natural Oak' }
            ]
        }
    ],
    // Key-value store lưu dữ liệu variant theo stable combination key
    variantsByKey: {},

    isSubmitting: false,

    // Quản lý sản phẩm hàng loạt (Bulk Product Creation)
    selectedBulkProducts: [], // [{ clientId, handle, title, descriptionHtml, payload, status: 'PENDING'|'RUNNING'|'SUCCESS'|'ERROR', error: null, links: null }]
    activeBulkProductId: null,
    selectedCsvHandles: new Set()
};

// ==========================================
// 2. INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    renderMediaGallery();
    renderOptions();
    renderTags();
    rebuildVariantMatrix();
    updateValidationState();
    updateSubmitButtonLabel();

    // Tự động tải danh sách tác giả inline sau khi trang nạp xong
    fetchAndRenderInlineAuthors();

    // Setup drag and drop for local upload
    const dropzone = document.querySelector('[onclick*="device-file-input"]');
    if (dropzone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, preventDefaults, false);
        });
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        dropzone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFilesList(files);
        });
    }
});

// ==========================================
// 3. MEDIA MANAGEMENT
// ==========================================
function handleDeviceFileSelect(event) {
    const files = event.target.files;
    handleFilesList(files);
    event.target.value = ''; // Reset input
}

function handleFilesList(files) {
    if (!files || files.length === 0) return;
    Array.from(files).forEach(file => {
        if (!file.type.startsWith('image/')) return;
        const previewUrl = URL.createObjectURL(file);
        state.media.push({
            id: 'med_' + Math.random().toString(36).substr(2, 9),
            kind: 'device',
            file: file,
            previewUrl: previewUrl,
            url: '',
            position: state.media.length + 1
        });
    });
    renderMediaGallery();
    updateValidationState();
}

function handleAddMediaUrl() {
    const input = document.getElementById('image-url-input');
    const url = (input.value || '').trim();
    if (!url) return;

    state.media.push({
        id: 'med_' + Math.random().toString(36).substr(2, 9),
        kind: 'url',
        file: null,
        previewUrl: url,
        url: url,
        position: state.media.length + 1
    });

    input.value = '';
    renderMediaGallery();
    updateValidationState();
}

function removeMediaItem(id) {
    state.media = state.media.filter(m => m.id !== id);
    // Cập nhật lại position
    state.media.forEach((m, idx) => m.position = idx + 1);
    renderMediaGallery();
    updateValidationState();
}

function moveMediaItem(index, direction) {
    const targetIdx = index + direction;
    if (targetIdx < 0 || targetIdx >= state.media.length) return;
    const temp = state.media[index];
    state.media[index] = state.media[targetIdx];
    state.media[targetIdx] = temp;
    state.media.forEach((m, idx) => m.position = idx + 1);
    renderMediaGallery();
}

function renderMediaGallery() {
    const gallery = document.getElementById('media-gallery');
    const badge = document.getElementById('media-count-badge');
    badge.textContent = `${state.media.length} ảnh`;

    if (state.media.length === 0) {
        gallery.innerHTML = `
            <div id="media-empty-placeholder" class="col-span-full py-8 text-center text-gray-400 text-sm font-medium">
                Chưa có hình ảnh nào được thêm. Vui lòng tải từ máy hoặc dán link URL.
            </div>
        `;
        return;
    }

    gallery.innerHTML = state.media.map((item, index) => `
        <div class="relative group rounded-xl overflow-hidden border border-gray-200 bg-white aspect-square flex items-center justify-center shadow-2xs">
            <img src="${item.previewUrl}" alt="Media ${index + 1}" class="w-full h-full object-cover">
            
            ${index === 0 ? '<span class="absolute top-1.5 left-1.5 bg-black/80 text-white text-sm font-bold px-2 py-0.5 rounded shadow-sm">Ảnh bìa</span>' : ''}
            
            <!-- Controls overlay -->
            <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-1.5">
                ${index > 0 ? `
                    <button type="button" onclick="moveMediaItem(${index}, -1)" class="p-1.5 bg-white/90 hover:bg-white text-gray-800 rounded-md transition-all shadow-sm" title="Chuyển về trước">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg>
                    </button>
                ` : ''}
                
                <button type="button" onclick="removeMediaItem('${item.id}')" class="p-1.5 bg-red-600/90 hover:bg-red-600 text-white rounded-md transition-all shadow-sm" title="Xóa ảnh">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
                
                ${index < state.media.length - 1 ? `
                    <button type="button" onclick="moveMediaItem(${index}, 1)" class="p-1.5 bg-white/90 hover:bg-white text-gray-800 rounded-md transition-all shadow-sm" title="Chuyển về sau">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

// ==========================================
// 4. VARIATION & CARTESIAN ENGINE
// ==========================================
function handleAddOption() {
    if (state.options.length >= 3) {
        alert("Shopify chỉ hỗ trợ tối đa 3 tùy chọn (Options) cho mỗi sản phẩm.");
        return;
    }
    const defaultNames = ['Size', 'Material', 'Finish', 'Style'];
    const usedNames = state.options.map(o => o.name.toLowerCase());
    const nextName = defaultNames.find(n => !usedNames.includes(n.toLowerCase())) || 'Option';

    state.options.push({
        clientId: 'opt_' + Math.random().toString(36).substr(2, 9),
        name: nextName,
        isEditing: true,
        values: []
    });

    renderOptions();
    rebuildVariantMatrix();
    updateValidationState();
    updateSubmitButtonLabel();
}

function handleRemoveOption(optIndex) {
    if (state.options.length <= 1) {
        alert("Sản phẩm bắt buộc phải có ít nhất 1 tùy chọn.");
        return;
    }
    state.options.splice(optIndex, 1);
    renderOptions();
    rebuildVariantMatrix();
    updateValidationState();
    updateSubmitButtonLabel();
}

function toggleOptionEditing(optIndex) {
    state.options[optIndex].isEditing = !state.options[optIndex].isEditing;
    renderOptions();
}

function handleOptionNameChange(optIndex, val) {
    state.options[optIndex].name = val.trim();
    rebuildVariantMatrix();
    updateValidationState();
    updateSubmitButtonLabel();
}

function handleAddOptionValue(optIndex, inputEl) {
    const rawVal = (inputEl.value || '').trim();
    if (!rawVal) return;

    // Tách các giá trị nếu người dùng gõ nhiều giá trị bằng dấu phẩy
    const pieces = rawVal.split(',').map(p => p.trim()).filter(p => p);
    const opt = state.options[optIndex];

    pieces.forEach(p => {
        const lower = p.toLowerCase();
        const exists = opt.values.some(v => v.label.toLowerCase() === lower);
        if (!exists) {
            opt.values.push({
                clientId: 'val_' + Math.random().toString(36).substr(2, 9),
                label: p
            });
        }
    });

    inputEl.value = '';
    renderOptions();
    rebuildVariantMatrix();
    updateValidationState();
    updateSubmitButtonLabel();
}

function handleRemoveOptionValue(optIndex, valIndex) {
    const opt = state.options[optIndex];
    opt.values.splice(valIndex, 1);
    renderOptions();
    rebuildVariantMatrix();
    updateValidationState();
    updateSubmitButtonLabel();
}

function renderOptions() {
    const container = document.getElementById('options-list-container');
    const addBtn = document.getElementById('btn-add-option');
    if (addBtn) {
        addBtn.style.display = state.options.length >= 3 ? 'none' : 'inline-flex';
    }

    container.innerHTML = state.options.map((opt, optIdx) => `
        <div class="border border-gray-200 rounded-xl bg-white p-5 shadow-2xs space-y-4">
            <!-- Header Option Row -->
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <span class="text-gray-400 cursor-grab" title="Kéo sắp xếp">
                        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M7 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm6-12a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/></svg>
                    </span>
                    <span class="text-sm font-bold uppercase tracking-wider text-gray-500">Tùy chọn ${optIdx + 1}</span>
                </div>
                <div class="flex items-center gap-2">
                    <button type="button" onclick="handleRemoveOption(${optIdx})" class="px-3 py-1 text-sm font-bold text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors">
                        Delete
                    </button>
                    <button type="button" onclick="toggleOptionEditing(${optIdx})" class="px-3.5 py-1 text-sm font-bold ${opt.isEditing ? 'bg-black text-white hover:bg-neutral-800' : 'bg-gray-100 text-gray-800 hover:bg-gray-200'} rounded-lg transition-colors">
                        ${opt.isEditing ? 'Done' : 'Edit'}
                    </button>
                </div>
            </div>

            <!-- Option Name Input (Giống UI Shopify Admin) -->
            <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1">Option name</label>
                <input type="text" value="${opt.name}" ${opt.isEditing ? '' : 'readonly'} onchange="handleOptionNameChange(${optIdx}, this.value)" placeholder="Ví dụ: Color, Size..." class="w-full bg-gray-50 border border-gray-300 text-sm font-semibold rounded-lg px-3 py-2 outline-none focus:ring-2 focus:ring-indigo-500 ${opt.isEditing ? 'focus:bg-white' : 'bg-gray-100 text-gray-600'} transition-all">
            </div>

            <!-- Option Values List & Input -->
            <div>
                <label class="block text-sm font-semibold text-gray-700 mb-1.5">Option values</label>
                <div class="flex flex-wrap items-center gap-2 p-2 bg-gray-50 border border-gray-300 rounded-lg min-h-[44px]">
                    ${opt.values.map((v, valIdx) => `
                        <span class="tag-pill">
                            <span>${v.label}</span>
                            ${opt.isEditing ? `
                                <button type="button" onclick="handleRemoveOptionValue(${optIdx}, ${valIdx})" class="btn-remove-tag w-[22px] h-[22px] min-w-[22px] min-h-[22px] inline-flex items-center justify-center rounded-full bg-gray-200 text-gray-600 hover:bg-red-500 hover:text-white transition-all focus:outline-none cursor-pointer" title="Xóa giá trị">
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"></path></svg>
                                </button>
                            ` : ''}
                        </span>
                    `).join('')}
                    ${opt.isEditing ? `
                        <input type="text" placeholder="Add a value..." onkeydown="if(event.key==='Enter'||event.key===','){event.preventDefault();handleAddOptionValue(${optIdx}, this);}" class="bg-transparent border-none text-sm text-gray-900 outline-none flex-1 min-w-[100px]">
                    ` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

/**
 * Tái tạo ma trận biến thể theo tích Descartes.
 * Sử dụng combination key ổn định dựa trên value clientId để không làm mất giá & SKU.
 */
function rebuildVariantMatrix() {
    const validOptions = state.options.filter(o => o.name.trim() && o.values.length > 0);
    const tbody = document.getElementById('variant-matrix-tbody');
    const summary = document.getElementById('variant-matrix-summary');

    if (validOptions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="px-4 py-8 text-center text-gray-400 text-sm">
                    Vui lòng nhập tên tùy chọn và ít nhất 1 giá trị để tạo ma trận biến thể.
                </td>
            </tr>
        `;
        summary.textContent = '0 tùy chọn • 0 biến thể';
        return;
    }

    // Tính Cartesian product
    const optionArrays = validOptions.map(o => o.values.map(v => ({
        optionName: o.name,
        valueId: v.clientId,
        valueLabel: v.label
    })));

    function cartesian(arrays) {
        return arrays.reduce((acc, curr) => {
            const res = [];
            acc.forEach(a => {
                curr.forEach(c => {
                    res.push([...a, c]);
                });
            });
            return res;
        }, [[]]);
    }

    const combinations = cartesian(optionArrays);
    summary.textContent = `${validOptions.length} tùy chọn • ${combinations.length} biến thể`;

    // Tối ưu render ma trận biến thể bằng DocumentFragment (tránh reflow lặp lại)
    const fragment = document.createDocumentFragment();
    const tempTbody = document.createElement('tbody');

    tempTbody.innerHTML = combinations.map((comb, rowIdx) => {
        // Sinh stable key
        const combKey = comb.map(c => c.valueId).join('_');
        const title = comb.map(c => c.valueLabel).join(' / ');

        // Khởi tạo state cho row nếu chưa có
        if (!state.variantsByKey[combKey]) {
            state.variantsByKey[combKey] = {
                price: '',
                compareAtPrice: '',
                sku: '',
                barcode: ''
            };
        }
        const rowData = state.variantsByKey[combKey];

        const pVal = parseFloat(rowData.price);
        const cVal = parseFloat(rowData.compareAtPrice);
        const isCompareInvalid = (!isNaN(pVal) && !isNaN(cVal) && cVal <= pVal);

        return `
            <tr class="hover:bg-gray-50/70 transition-colors ${isCompareInvalid ? 'bg-red-50/40' : ''}" data-comb-key="${combKey}">
                <td class="px-4 py-3 font-semibold text-gray-900">
                    <span class="inline-block px-2.5 py-1 bg-gray-100 rounded-md text-sm text-gray-800 border border-gray-200">
                        ${title}
                    </span>
                </td>
                <td class="px-3 py-3">
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-gray-400 font-bold">$</span>
                        <input type="number" step="0.01" min="0" value="${rowData.price}" oninput="handleVariantFieldChange('${combKey}', 'price', this.value)" placeholder="0.00" class="w-full pl-6 pr-2 py-1.5 bg-gray-50 border border-gray-300 rounded-lg text-sm font-semibold outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white">
                    </div>
                </td>
                <td class="px-3 py-3">
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-gray-400 font-bold">$</span>
                        <input type="number" step="0.01" min="0" value="${rowData.compareAtPrice}" oninput="handleVariantFieldChange('${combKey}', 'compareAtPrice', this.value)" placeholder="0.00" class="w-full pl-6 pr-2 py-1.5 bg-gray-50 border ${isCompareInvalid ? 'border-red-500 ring-1 ring-red-400 bg-red-50/50' : 'border-gray-300'} rounded-lg text-sm font-semibold outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white">
                    </div>
                    ${isCompareInvalid ? '<p class="text-sm text-red-600 font-medium mt-1">Compare-at price phải > Price</p>' : ''}
                </td>
                <td class="px-3 py-3">
                    <input type="text" value="${rowData.sku}" oninput="handleVariantFieldChange('${combKey}', 'sku', this.value)" placeholder="Mã SKU..." class="w-full px-2.5 py-1.5 bg-gray-50 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white font-mono">
                </td>
                <td class="px-3 py-3">
                    <input type="text" value="${rowData.barcode}" oninput="handleVariantFieldChange('${combKey}', 'barcode', this.value)" placeholder="Mã Barcode..." class="w-full px-2.5 py-1.5 bg-gray-50 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white font-mono">
                </td>
            </tr>
        `;
    }).join('');

    while (tempTbody.firstChild) {
        fragment.appendChild(tempTbody.firstChild);
    }
    if (typeof tbody.replaceChildren === 'function') {
        tbody.replaceChildren(fragment);
    } else {
        tbody.innerHTML = '';
        tbody.appendChild(fragment);
    }
}

function handleVariantFieldChange(combKey, field, val) {
    if (!state.variantsByKey[combKey]) {
        state.variantsByKey[combKey] = {};
    }
    state.variantsByKey[combKey][field] = val;
    if (field === 'price' || field === 'compareAtPrice') {
        const row = document.querySelector(`tr[data-comb-key="${combKey}"]`);
        if (row) {
            const pVal = parseFloat(state.variantsByKey[combKey].price);
            const cVal = parseFloat(state.variantsByKey[combKey].compareAtPrice);
            const isCompareInvalid = (!isNaN(pVal) && !isNaN(cVal) && cVal <= pVal);
            if (isCompareInvalid) {
                row.classList.add('bg-red-50/40');
            } else {
                row.classList.remove('bg-red-50/40');
            }
        }
    }
    updateValidationState();
}

function promptBulkPricing() {
    const price = prompt("Nhập Giá Bán ($) cho toàn bộ các biến thể:", "129.00");
    if (price === null) return;
    const compareAt = prompt("Nhập Giá So Sánh ($) cho toàn bộ các biến thể:", "159.00");
    if (compareAt === null) return;

    const baseSkuPrefix = prompt("Nhập tiền tố SKU (ví dụ: WRY-SHELF):", "WRY-PROD");

    let counter = 1;
    const timestamp = Date.now().toString().slice(-6);

    Object.keys(state.variantsByKey).forEach(key => {
        state.variantsByKey[key].price = price;
        state.variantsByKey[key].compareAtPrice = compareAt;
        if (baseSkuPrefix) {
            state.variantsByKey[key].sku = `${baseSkuPrefix}-${counter}`;
            state.variantsByKey[key].barcode = `8935${timestamp}${String(counter).padStart(2, '0')}`;
        }
        counter++;
    });

    rebuildVariantMatrix();
    updateValidationState();
    updateSubmitButtonLabel();
}

// ==========================================
// 5. TAGS MANAGEMENT
// ==========================================
function handleTagKeydown(e) {
    if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        const input = document.getElementById('tag-input');
        const val = (input.value || '').trim();
        if (val && !state.tags.includes(val)) {
            state.tags.push(val);
            input.value = '';
            renderTags();
            updateValidationState();
        }
    }
}

function removeTag(tag) {
    state.tags = state.tags.filter(t => t !== tag);
    renderTags();
    updateValidationState();
}

function renderTags() {
    const container = document.getElementById('tags-container');
    container.innerHTML = state.tags.map(t => `
        <span class="tag-pill">
            <span>${escapeHtml(t)}</span>
            <button type="button" onclick="removeTag('${escapeHtml(t)}')" class="btn-remove-tag w-[22px] h-[22px] min-w-[22px] min-h-[22px] inline-flex items-center justify-center rounded-full bg-gray-200 text-gray-600 hover:bg-red-500 hover:text-white transition-all focus:outline-none cursor-pointer" title="Xóa thẻ ${escapeHtml(t)}">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </span>
    `).join('');
}

// ==========================================
// 6. CATEGORY MODAL & TAXONOMY
// ==========================================
function openCategoryModal() {
    document.getElementById('category-modal').classList.remove('hidden');
    handleCategorySearch('');
}

function closeCategoryModal() {
    document.getElementById('category-modal').classList.add('hidden');
}

let categorySearchDebounce = null;
function handleCategorySearch(keyword) {
    clearTimeout(categorySearchDebounce);
    categorySearchDebounce = setTimeout(async () => {
        const resultsEl = document.getElementById('category-search-results');
        resultsEl.innerHTML = '<p class="text-sm text-gray-400 text-center py-4">Đang tìm danh mục...</p>';
        try {
            const res = await fetch(`/api/taxonomy?search=${encodeURIComponent(keyword || '')}`);
            const data = await res.json();
            const nodes = data.nodes || [];
            if (nodes.length === 0) {
                resultsEl.innerHTML = '<p class="text-sm text-gray-400 text-center py-4">Không tìm thấy danh mục phù hợp.</p>';
                return;
            }
            resultsEl.innerHTML = nodes.map(n => `
                <div onclick="selectCategory('${n.id}', '${escapeHtml(n.fullName || n.name)}')" class="p-2.5 hover:bg-indigo-50 rounded-lg cursor-pointer transition-colors flex items-center justify-between">
                    <div>
                        <p class="text-sm font-bold text-gray-900">${n.name}</p>
                        <p class="text-sm text-gray-500">${n.fullName || n.name}</p>
                    </div>
                    <span class="text-sm text-indigo-600 font-bold">Chọn &rarr;</span>
                </div>
            `).join('');
        } catch (e) {
            resultsEl.innerHTML = `<p class="text-sm text-red-500 text-center py-4">Lỗi tải danh mục: ${e.message}</p>`;
        }
    }, 250);
}

function selectCategory(id, fullName) {
    state.selectedCategoryId = id;
    state.selectedCategoryName = fullName;
    document.getElementById('selected-category-id').value = id;
    document.getElementById('selected-category-name').value = fullName;
    closeCategoryModal();
    updateValidationState();
}

// ==========================================
// 7. INLINE PRODUCT AUTHORS MANAGEMENT
// ==========================================
async function fetchAndRenderInlineAuthors() {
    const loadingEl = document.getElementById('author-loading-indicator');
    const containerEl = document.getElementById('inline-authors-container');
    const emptyEl = document.getElementById('author-empty-state');
    const badgeEl = document.getElementById('author-count-badge');
    const hiddenInput = document.getElementById('selected-author-id');

    if (loadingEl) loadingEl.classList.remove('hidden');
    if (containerEl) {
        containerEl.classList.add('hidden');
        containerEl.innerHTML = '';
    }
    if (emptyEl) emptyEl.classList.add('hidden');
    if (badgeEl) badgeEl.textContent = 'Đang tải...';

    try {
        const res = await fetch(`/api/product-authors?store_type=${encodeURIComponent(state.currentStoreType)}`);
        const authors = await res.json();
        state.authors = Array.isArray(authors) ? authors : [];

        if (loadingEl) loadingEl.classList.add('hidden');

        if (state.authors.length === 0) {
            if (emptyEl) emptyEl.classList.remove('hidden');
            if (badgeEl) badgeEl.textContent = '0 tác giả';
            state.selectedAuthorId = '';
            state.selectedAuthorData = null;
            if (hiddenInput) hiddenInput.value = '';
            updateValidationState();
            return;
        }

        if (badgeEl) badgeEl.textContent = `${state.authors.length} tác giả có sẵn`;

        // Render các thẻ card author inline
        if (containerEl) {
            containerEl.innerHTML = state.authors.map(a => {
                const isSelected = state.selectedAuthorId === a.id;
                const displayName = a.name || a.displayName || 'Nghệ nhân';
                const roleText = a.role || a.slogan || a.handle || 'Nghệ nhân WRYDECO';
                const initial = displayName.charAt(0).toUpperCase();

                return `
                    <div id="author-card-${a.id}" onclick="selectInlineAuthor('${a.id}')" 
                         class="relative flex items-center justify-between p-3.5 rounded-xl border cursor-pointer transition-all ${isSelected ? 'border-2 border-indigo-600 bg-indigo-50/70 shadow-xs ring-2 ring-indigo-500/20' : 'border-gray-200 bg-white hover:border-indigo-300 hover:bg-gray-50/80'}">
                        <div class="flex items-center gap-3 min-w-0 pr-6">
                            ${a.image_url ? `
                                <img src="${a.image_url}" alt="${escapeHtml(displayName)}" class="w-10 h-10 rounded-full object-cover border border-gray-200 flex-shrink-0" onerror="this.outerHTML='<div class=\\'w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm flex-shrink-0\\'>${initial}</div>'">
                            ` : `
                                <div class="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm flex-shrink-0">
                                    ${initial}
                                </div>
                            `}
                            <div class="min-w-0">
                                <p class="text-sm font-bold text-gray-900 truncate">${escapeHtml(displayName)}</p>
                                <p class="text-sm text-gray-500 truncate">${escapeHtml(roleText)}</p>
                                ${a.exp_years ? `<span class="inline-block mt-0.5 px-1.5 py-0.2 text-sm font-semibold bg-gray-100 text-gray-600 rounded">${escapeHtml(a.exp_years)} năm kinh nghiệm</span>` : ''}
                            </div>
                        </div>
                        <div class="absolute right-3.5 top-1/2 -translate-y-1/2">
                            <div id="author-check-${a.id}" class="w-5 h-5 rounded-full flex items-center justify-center transition-all ${isSelected ? 'bg-indigo-600 text-white' : 'border-2 border-gray-300 text-transparent'}">
                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            containerEl.classList.remove('hidden');
        }

        updateValidationState();

    } catch (err) {
        console.error("Lỗi khi tải danh sách tác giả:", err);
        if (loadingEl) loadingEl.classList.add('hidden');
        if (emptyEl) {
            emptyEl.innerHTML = `<p class="text-sm font-semibold text-red-600">Lỗi kết nối khi tải danh sách tác giả: ${escapeHtml(err.message)}</p>`;
            emptyEl.classList.remove('hidden');
        }
        if (badgeEl) badgeEl.textContent = 'Lỗi nạp';
    }
}

function selectInlineAuthor(id) {
    const author = state.authors.find(a => a.id === id);
    if (!author) return;

    state.selectedAuthorId = id;
    state.selectedAuthorData = author;

    const hiddenInput = document.getElementById('selected-author-id');
    if (hiddenInput) hiddenInput.value = id;

    // Cập nhật viền active và radio checkmark
    state.authors.forEach(a => {
        const card = document.getElementById(`author-card-${a.id}`);
        const check = document.getElementById(`author-check-${a.id}`);
        if (!card || !check) return;

        if (a.id === id) {
            card.className = "relative flex items-center justify-between p-3.5 rounded-xl border cursor-pointer transition-all border-2 border-indigo-600 bg-indigo-50/70 shadow-xs ring-2 ring-indigo-500/20";
            check.className = "w-5 h-5 rounded-full flex items-center justify-center transition-all bg-indigo-600 text-white";
        } else {
            card.className = "relative flex items-center justify-between p-3.5 rounded-xl border cursor-pointer transition-all border-gray-200 bg-white hover:border-indigo-300 hover:bg-gray-50/80";
            check.className = "w-5 h-5 rounded-full flex items-center justify-center transition-all border-2 border-gray-300 text-transparent";
        }
    });

    updateValidationState();
}

// ==========================================
// 8. SEO HANDLERS
// ==========================================
function handleTitleInput(val) {
    document.getElementById('title-char-count').textContent = `${val.length} ký tự`;
    // Tự sinh SEO Title nếu SEO Title đang rỗng hoặc chưa bị sửa
    const seoTitleInput = document.getElementById('seo-title');
    if (seoTitleInput && !seoTitleInput.getAttribute('data-touched')) {
        const fullSeo = val ? `${val} | Wrydeco` : '';
        seoTitleInput.value = fullSeo;
        document.getElementById('seo-title-count').textContent = `${fullSeo.length} / 70 ký tự`;
        document.getElementById('seo-preview-title').textContent = fullSeo || 'Tiêu đề sản phẩm';
    }
    // Tự sinh URL Handle nếu Handle chưa bị sửa tay thủ công
    const handleInput = document.getElementById('product-handle');
    const slug = slugify(val);
    if (handleInput && !handleInput.getAttribute('data-touched')) {
        handleInput.value = slug;
        const previewSpan = document.getElementById('seo-preview-handle');
        if (previewSpan) previewSpan.textContent = slug || 'sample-product';
    } else if (!handleInput) {
        const previewSpan = document.getElementById('seo-preview-handle');
        if (previewSpan) previewSpan.textContent = slug || 'sample-product';
    }
    updateValidationState();
}

function handleCustomHandleInput(val) {
    const cleanVal = (val || '').trim();
    const handleInput = document.getElementById('product-handle');
    const resetBtn = document.getElementById('btn-reset-handle');
    
    // Đánh dấu người dùng đã tự chỉnh sửa thủ công
    if (handleInput) {
        handleInput.setAttribute('data-touched', 'true');
    }
    if (resetBtn) {
        resetBtn.classList.remove('hidden');
    }
    
    // Cập nhật preview
    const previewSpan = document.getElementById('seo-preview-handle');
    if (previewSpan) {
        previewSpan.textContent = cleanVal || 'sample-product';
    }
    updateValidationState();
}

function resetHandleFromTitle() {
    const handleInput = document.getElementById('product-handle');
    const resetBtn = document.getElementById('btn-reset-handle');
    const titleVal = document.getElementById('product-title')?.value || '';
    const slug = slugify(titleVal);

    if (handleInput) {
        handleInput.removeAttribute('data-touched');
        handleInput.value = slug;
    }
    if (resetBtn) {
        resetBtn.classList.add('hidden');
    }
    const previewSpan = document.getElementById('seo-preview-handle');
    if (previewSpan) {
        previewSpan.textContent = slug || 'sample-product';
    }
    updateValidationState();
}

function handleSeoTitleInput(val) {
    document.getElementById('seo-title-count').textContent = `${val.length} / 70 ký tự`;
    document.getElementById('seo-preview-title').textContent = val || 'Tiêu đề sản phẩm';
    document.getElementById('seo-title').setAttribute('data-touched', 'true');
    updateValidationState();
}

function handleSeoDescInput(val) {
    document.getElementById('seo-desc-count').textContent = `${val.length} / 160 ký tự`;
    document.getElementById('seo-preview-desc').textContent = val || 'Mô tả sản phẩm sẽ hiển thị tại đây...';
    updateValidationState();
}

function slugify(text) {
    return text.toString().toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-z0-9 -]/g, '')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .trim();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text;
    return div.innerHTML;
}

// ==========================================
// 9. SINGLE SOURCE OF TRUTH VALIDATION
// ==========================================
let isBatchUpdating = false;

function getMissingValidationFields() {
    const title = (document.getElementById('product-title')?.value || '').trim();
    const handle = (document.getElementById('product-handle')?.value || '').trim();
    const desc = (document.getElementById('product-desc')?.value || '').trim();
    const productType = (document.getElementById('product-type')?.value || '').trim();
    const categoryId = (document.getElementById('selected-category-id')?.value || '').trim();
    const status = (document.getElementById('product-status')?.value || '').trim();
    const vendor = (document.getElementById('product-vendor')?.value || '').trim();
    const seoTitle = (document.getElementById('seo-title')?.value || '').trim();
    const seoDesc = (document.getElementById('seo-desc')?.value || '').trim();
    const authorId = (document.getElementById('selected-author-id')?.value || '').trim();
    const richDesc = (document.getElementById('rich-description')?.value || '').trim();
    const aeoHtml = (document.getElementById('aeo-html')?.value || '').trim();

    // Checked checkboxes
    const checkedInterior = Array.from(document.querySelectorAll('input[name="interior_style"]:checked')).map(cb => cb.value);
    const checkedRoom = Array.from(document.querySelectorAll('input[name="room_type"]:checked')).map(cb => cb.value);

    // Variants validity
    const validOptions = state.options.filter(o => o.name.trim() && o.values.length > 0);
    let variantsValid = false;
    let variantsReason = '';

    if (validOptions.length === 0) {
        variantsReason = 'Chưa thiết lập tùy chọn và giá trị biến thể';
    } else if (validOptions.length > 3) {
        variantsReason = 'Số lượng tùy chọn không được vượt quá 3';
    } else {
        const optionArrays = validOptions.map(o => o.values.map(v => v.clientId));
        const combs = optionArrays.reduce((acc, curr) => {
            const res = [];
            acc.forEach(a => curr.forEach(c => res.push([...a, c])));
            return res;
        }, [[]]);

        const variantsCount = combs.length;
        if (variantsCount === 0) {
            variantsReason = 'Chưa có biến thể nào được tạo';
        } else if (variantsCount > 2048) {
            variantsReason = 'Số lượng biến thể vượt quá giới hạn 2048';
        } else {
            let allComplete = true;
            for (const c of combs) {
                const k = c.join('_');
                const row = state.variantsByKey[k];
                if (!row) {
                    allComplete = false;
                    variantsReason = 'Một số biến thể chưa được thiết lập dữ liệu';
                    break;
                }
                if (!row.price || parseFloat(row.price) < 0) {
                    allComplete = false;
                    variantsReason = 'Giá bán biến thể chưa hợp lệ (phải >= 0)';
                    break;
                }
                if (!row.compareAtPrice || parseFloat(row.compareAtPrice) <= parseFloat(row.price)) {
                    allComplete = false;
                    variantsReason = 'Giá so sánh phải lớn hơn Giá bán cho từng biến thể';
                    break;
                }
                if (!row.sku || !row.sku.trim()) {
                    allComplete = false;
                    variantsReason = 'Thiếu mã SKU cho biến thể';
                    break;
                }
                if (!row.barcode || !row.barcode.trim()) {
                    allComplete = false;
                    variantsReason = 'Thiếu Barcode cho biến thể';
                    break;
                }
            }
            variantsValid = allComplete;
        }
    }

    const missing = [];
    if (state.media.length === 0) {
        missing.push({ label: 'Hình ảnh sản phẩm', hint: 'Thêm ít nhất 1 ảnh từ máy tính hoặc link URL', targetId: 'image-url-input' });
    }
    if (!title) {
        missing.push({ label: 'Tên sản phẩm', hint: 'Nhập tên sản phẩm', targetId: 'product-title' });
    }
    if (!desc) {
        missing.push({ label: 'Mô tả ngắn', hint: 'Nhập mô tả tóm tắt cho sản phẩm', targetId: 'product-desc' });
    }
    if (!productType) {
        missing.push({ label: 'Loại sản phẩm (Type)', hint: 'Nhập loại sản phẩm (ví dụ: Wall Shelf, Decor...)', targetId: 'product-type' });
    }
    if (!categoryId) {
        missing.push({ label: 'Danh mục (Category)', hint: 'Bấm nút "Chọn" để chọn danh mục chuẩn Shopify', targetId: 'product-category-name' });
    }
    if (!status) {
        missing.push({ label: 'Trạng thái (Status)', hint: 'Chọn trạng thái Draft hoặc Active', targetId: 'product-status' });
    }
    if (!vendor) {
        missing.push({ label: 'Nhà cung cấp (Vendor)', hint: 'Chọn hoặc nhập nhà cung cấp', targetId: 'product-vendor' });
    }
    if (state.tags.length === 0) {
        missing.push({ label: 'Thẻ sản phẩm (Tags)', hint: 'Nhập ít nhất 1 tag và nhấn Enter', targetId: 'tagInput' });
    }
    if (!seoTitle) {
        missing.push({ label: 'SEO Title', hint: 'Nhập tiêu đề trang hiển thị trên Google', targetId: 'seo-title' });
    }
    if (!seoDesc) {
        missing.push({ label: 'SEO Description', hint: 'Nhập mô tả meta hiển thị trên Google', targetId: 'seo-desc' });
    }
    if (!authorId) {
        missing.push({ label: 'Nghệ nhân / Tác giả', hint: 'Chọn 1 nghệ nhân chế tác từ danh sách', targetId: 'author-search-inline' });
    }
    if (!richDesc) {
        missing.push({ label: 'Mô tả mở rộng (Rich Description)', hint: 'Nhập nội dung mô tả chi tiết sản phẩm', targetId: 'rich-description' });
    }
    if (!aeoHtml) {
        missing.push({ label: 'Nội dung tối ưu tìm kiếm AEO', hint: 'Nhập câu hỏi/đáp và tóm tắt cho AI tìm kiếm', targetId: 'aeo-html' });
    }
    if (checkedInterior.length === 0) {
        missing.push({ label: 'Phong cách nội thất (Interior Style)', hint: 'Chọn ít nhất 1 phong cách phù hợp', targetId: 'interior-style-container' });
    }
    if (checkedRoom.length === 0) {
        missing.push({ label: 'Không gian phòng (Room Type)', hint: 'Chọn ít nhất 1 không gian phòng', targetId: 'room-type-container' });
    }
    if (!variantsValid) {
        missing.push({ label: 'Biến thể sản phẩm', hint: variantsReason || 'Điền đầy đủ Giá bán, Giá so sánh (> Giá bán), SKU và Barcode', targetId: 'variant-matrix-tbody' });
    }

    const completedCount = 16 - missing.length;
    const isAllValid = (missing.length === 0);

    return {
        isAllValid,
        completedCount,
        missing
    };
}

function updateValidationState() {
    if (isBatchUpdating) return;
    
    const valInfo = getMissingValidationFields();
    const isAllValid = valInfo.isAllValid;
    const completedCount = valInfo.completedCount;

    // Cập nhật Badge trên Header
    const badge = document.getElementById('form-validation-badge');
    if (badge) {
        if (isAllValid) {
            badge.className = 'inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-sm font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200';
            badge.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500"></span><span>Sẵn sàng: 16/16 trường hợp lệ</span>';
        } else {
            badge.className = 'inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-sm font-semibold bg-amber-50 text-amber-800 border border-amber-200';
            badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span><span>Đã hoàn thành ${completedCount}/16 trường bắt buộc</span>`;
        }
    }

    // Cập nhật Nút Submit & Hint Text
    const submitBtn = document.getElementById('btn-submit-product');
    const hintIcon = document.getElementById('submit-hint-icon');
    const hintText = document.getElementById('submit-hint-text');

    if (submitBtn && !state.isSubmitting) {
        // KHONG set submitBtn.disabled = true de nguoi dung luon click duoc va nhan huong dan
        submitBtn.disabled = false;
        if (isAllValid) {
            submitBtn.className = 'w-full sm:w-auto min-w-[260px] px-8 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-base rounded-xl cursor-pointer shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2.5';
            if (hintIcon) hintIcon.className = 'text-emerald-600 flex-shrink-0';
            if (hintText) {
                hintText.className = 'text-[16px] text-emerald-700 font-medium';
                hintText.textContent = 'Mọi thông tin đã đầy đủ (16/16). Bạn có thể tiến hành tạo sản phẩm ngay bây giờ.';
            }
        } else {
            submitBtn.className = 'w-full sm:w-auto min-w-[260px] px-8 py-2.5 bg-amber-500 hover:bg-amber-600 text-white font-bold text-base rounded-xl cursor-pointer shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2.5';
            if (hintIcon) hintIcon.className = 'text-amber-500 flex-shrink-0';
            if (hintText) {
                hintText.className = 'text-[16px] text-gray-700 font-medium';
                hintText.textContent = `Vui lòng hoàn thành tất cả 16 trường có dấu * (${completedCount}/16) để tạo sản phẩm.`;
            }
        }
    }
}

// ==========================================
// 10. SUBMISSION & ERROR HANDLING
// ==========================================
function dismissErrorSection() {
    document.getElementById('create-error-section').classList.add('hidden');
}

function scrollToErrorSection() {
    const sec = document.getElementById('create-error-section');
    if (!sec) return;
    sec.classList.remove('hidden');

    const header = document.querySelector('header');
    const headerHeight = header ? header.offsetHeight : 64;
    const extraOffset = 24; // Khoảng cách đệm an toàn dưới header
    const totalOffset = headerHeight + extraOffset;

    const elementRect = sec.getBoundingClientRect();
    const absoluteElementTop = elementRect.top + window.pageYOffset;
    const targetScrollTop = Math.max(0, absoluteElementTop - totalOffset);

    window.scrollTo({
        top: targetScrollTop,
        behavior: 'smooth'
    });
}

function showErrorSection(phase, errors) {
    const sec = document.getElementById('create-error-section');
    const phaseBadge = document.getElementById('error-phase-badge');
    const list = document.getElementById('error-items-list');

    phaseBadge.textContent = phase || 'UNKNOWN';
    list.innerHTML = (errors || []).map(err => `
        <li>
            <strong class="font-bold">[${err.field || 'General'}]</strong>: ${escapeHtml(err.message)}
        </li>
    `).join('');

    sec.classList.remove('hidden');
    scrollToErrorSection();
}

async function handleFormSubmit() {
    if (state.isSubmitting) return;

    // Nếu đang có danh sách sản phẩm hàng loạt (> 1 sản phẩm)
    if (state.selectedBulkProducts && state.selectedBulkProducts.length > 1) {
        await startBulkCreationWorkflow();
        return;
    }

    // 0. Kiem tra tinh hop le cua 16 truong Single Source of Truth
    const valInfo = getMissingValidationFields();
    if (!valInfo.isAllValid) {
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'warning',
                title: 'Chưa đủ điều kiện tạo sản phẩm',
                html: `
                    <div class="text-left text-sm text-gray-700">
                        <p class="font-bold text-amber-800 mb-2">
                            Bạn đã hoàn thành <b>${valInfo.completedCount}/16</b> trường bắt buộc. Còn thiếu <b>${valInfo.missing.length}</b> mục sau:
                        </p>
                        <ul class="list-disc pl-5 space-y-1.5 max-h-60 overflow-y-auto pr-1">
                            ${valInfo.missing.map(m => `
                                <li>
                                    <strong class="text-gray-900">${escapeHtml(m.label)}:</strong> 
                                    <span class="text-gray-600">${escapeHtml(m.hint)}</span>
                                </li>
                            `).join('')}
                        </ul>
                    </div>
                `,
                confirmButtonText: 'Bổ sung ngay',
                confirmButtonColor: '#4f46e5',
                showCancelButton: true,
                cancelButtonText: 'Đóng',
                cancelButtonColor: '#9ca3af',
                customClass: {
                    popup: '!rounded-2xl !p-6'
                }
            }).then((res) => {
                if (res.isConfirmed && valInfo.missing.length > 0) {
                    const first = valInfo.missing[0];
                    const targetEl = document.getElementById(first.targetId) || document.querySelector(`[name="${first.targetId}"]`);
                    if (targetEl) {
                        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        if (typeof targetEl.focus === 'function') targetEl.focus();
                    }
                }
            });
        } else {
            alert(`Vui lòng hoàn thành đủ 16 trường có dấu *. Còn thiếu: ${valInfo.missing.map(m => m.label).join(', ')}`);
        }
        return;
    }

    // 1. Chuẩn bị payload đầy đủ
    const title = (document.getElementById('product-title')?.value || '').trim();
    const handle = (document.getElementById('product-handle')?.value || '').trim();
    const desc = (document.getElementById('product-desc')?.value || '').trim();
    const productType = (document.getElementById('product-type')?.value || '').trim();
    const categoryId = (document.getElementById('selected-category-id')?.value || '').trim();
    const status = (document.getElementById('product-status')?.value || 'DRAFT').trim();
    const vendor = (document.getElementById('product-vendor')?.value || 'Wrydeco').trim();
    const seoTitle = (document.getElementById('seo-title')?.value || '').trim();
    const seoDesc = (document.getElementById('seo-desc')?.value || '').trim();
    const authorId = (document.getElementById('selected-author-id')?.value || '').trim();
    const richDesc = (document.getElementById('rich-description')?.value || '').trim();
    const aeoHtml = (document.getElementById('aeo-html')?.value || '').trim();

    const checkedInterior = Array.from(document.querySelectorAll('input[name="interior_style"]:checked')).map(cb => cb.value);
    const checkedRoom = Array.from(document.querySelectorAll('input[name="room_type"]:checked')).map(cb => cb.value);

    // Variants list mapping
    const validOptions = state.options.filter(o => o.name.trim() && o.values.length > 0);
    const optionArrays = validOptions.map(o => o.values.map(v => ({
        optionName: o.name,
        valueId: v.clientId,
        valueLabel: v.label
    })));

    const combs = optionArrays.reduce((acc, curr) => {
        const res = [];
        acc.forEach(a => curr.forEach(c => res.push([...a, c])));
        return res;
    }, [[]]);

    const variantsPayload = combs.map(comb => {
        const combKey = comb.map(c => c.valueId).join('_');
        const row = state.variantsByKey[combKey] || {};
        return {
            optionValues: comb.map(c => ({
                optionName: c.optionName,
                name: c.valueLabel
            })),
            price: row.price,
            compareAtPrice: row.compareAtPrice,
            sku: row.sku,
            barcode: row.barcode
        };
    });

    // Options payload
    const optionsPayload = validOptions.map(o => ({
        name: o.name,
        values: o.values.map(v => ({ label: v.label }))
    }));

    // Media metadata & files
    const mediaMetadata = [];
    const localFiles = [];

    state.media.forEach((m, idx) => {
        if (m.kind === 'url') {
            mediaMetadata.push({
                kind: 'url',
                url: m.url,
                position: idx + 1
            });
        } else if (m.kind === 'device' && m.file) {
            localFiles.push(m.file);
            mediaMetadata.push({
                kind: 'device',
                fileIndex: localFiles.length - 1,
                position: idx + 1
            });
        }
    });

    const payloadObj = {
        store_type: state.currentStoreType,
        title,
        handle,
        descriptionHtml: desc,
        productType,
        categoryId,
        status,
        vendor,
        tags: state.tags,
        seo: {
            title: seoTitle,
            description: seoDesc
        },
        authorId,
        richDescription: richDesc,
        aeoHtml,
        interiorStyle: checkedInterior,
        roomType: checkedRoom,
        options: optionsPayload,
        variants: variantsPayload,
        media: mediaMetadata
    };

    // 1.5. Chốt chặn xác nhận trước khi tạo (Confirmation Gate)
    if (typeof Swal !== 'undefined') {
        const storeName = state.currentStoreType === 'custom' ? 'Store Riêng (qua US Proxy Gate)' : 'Store Mặc định';
        const confirmResult = await Swal.fire({
            title: 'Xác nhận tạo sản phẩm',
            html: `
                <div class="text-left text-sm text-gray-700 space-y-3">
                    <p>Bạn có chắc chắn muốn tiến hành tạo sản phẩm này lên <b>${escapeHtml(storeName)}</b>?</p>
                    <div class="p-3.5 bg-gray-50 rounded-xl border border-gray-200 space-y-2 text-sm font-medium">
                        <div>
                            <span class="text-gray-500 font-semibold block text-sm">Tiêu đề:</span>
                            <span class="text-gray-900 font-bold text-sm block">${escapeHtml(title)}</span>
                        </div>
                        <div>
                            <span class="text-gray-500 font-semibold block text-sm">Handle:</span>
                            <code class="text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded text-sm font-mono font-bold">${escapeHtml(handle)}</code>
                        </div>
                        <div class="flex items-center gap-4 text-sm text-gray-700 pt-1 border-t border-gray-200/60">
                            <span>Biến thể: <b class="text-gray-900">${variantsPayload.length}</b></span>
                            <span>Ảnh: <b class="text-gray-900">${mediaMetadata.length}</b></span>
                            <span>Trạng thái: <b class="text-gray-900">${status}</b></span>
                        </div>
                    </div>
                </div>
            `,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Tiến hành tạo',
            cancelButtonText: 'Hủy bỏ',
            confirmButtonColor: '#4f46e5',
            cancelButtonColor: '#6b7280',
            reverseButtons: true,
            focusCancel: false,
            customClass: {
                popup: '!rounded-2xl !p-6'
            }
        });
        if (!confirmResult.isConfirmed) {
            return;
        }
    }

    // 2. Chuyển sang trạng thái submitting
    state.isSubmitting = true;
    const submitBtn = document.getElementById('btn-submit-product');
    const spinner = document.getElementById('submit-spinner');
    const submitBtnIcon = document.getElementById('submit-btn-icon');
    const btnText = document.getElementById('submit-btn-text');

    if (submitBtn) submitBtn.disabled = true;
    if (spinner) spinner.classList.remove('hidden');
    if (submitBtnIcon) submitBtnIcon.classList.add('hidden');
    if (btnText) btnText.textContent = `Đang tạo sản phẩm lên ${state.currentStoreType === 'custom' ? 'Store Riêng' : 'Store Mặc định'}...`;
    dismissErrorSection();

    try {
        const formData = new FormData();
        formData.append('payload', JSON.stringify(payloadObj));
        localFiles.forEach(f => {
            formData.append('media_files', f);
        });

        const resp = await fetch('/api/products/create', {
            method: 'POST',
            body: formData
        });

        const result = await resp.json();

        if (resp.ok && result.success) {
            if (btnText) btnText.textContent = 'Tạo thành công!';
            state.isSubmitting = false;
            if (submitBtn) submitBtn.disabled = false;
            if (spinner) spinner.classList.add('hidden');
            if (submitBtnIcon) submitBtnIcon.classList.remove('hidden');

            const prod = result.product || { id: '', handle: handle, title: title };
            showCreatedProductSuccessSection(prod, state.currentStoreType);
        } else {
            showErrorSection(result.phase || 'API_ERROR', result.errors || [{ field: 'Request', message: result.message || 'Lỗi không xác định' }]);
            state.isSubmitting = false;
            if (submitBtn) submitBtn.disabled = false;
            if (spinner) spinner.classList.add('hidden');
            if (submitBtnIcon) submitBtnIcon.classList.remove('hidden');
            const failCount = (state.selectedBulkProducts || []).length || 1;
            if (btnText) btnText.textContent = `Thử lại tạo ${failCount} sản phẩm`;
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'error',
                    title: 'Tạo sản phẩm thất bại',
                    text: result.message || 'Vui lòng kiểm tra lại thông tin chi tiết lỗi bên dưới.',
                    confirmButtonColor: '#ef4444'
                }).then(() => {
                    scrollToErrorSection();
                });
            }
        }
    } catch (networkErr) {
        showErrorSection('NETWORK_ERROR', [{ field: 'Network', message: networkErr.message || 'Không thể kết nối tới máy chủ.' }]);
        state.isSubmitting = false;
        if (submitBtn) submitBtn.disabled = false;
        if (spinner) spinner.classList.add('hidden');
        if (submitBtnIcon) submitBtnIcon.classList.remove('hidden');
        const failCount = (state.selectedBulkProducts || []).length || 1;
        if (btnText) btnText.textContent = `Thử lại tạo ${failCount} sản phẩm`;
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'error',
                title: 'Lỗi kết nối',
                text: networkErr.message || 'Không thể kết nối tới máy chủ API.',
                confirmButtonColor: '#ef4444'
            }).then(() => {
                scrollToErrorSection();
            });
        }
    }
}


// ==========================================
// 11. SHOPIFY PRODUCT EXPORT CSV IMPORT ENGINE
// ==========================================

let parsedCsvProducts = {};

function triggerCsvImport() {
    const input = document.getElementById('csv-file-input');
    if (input) {
        input.value = '';
        input.click();
    }
}

function handleCsvFileSelected(event) {
    const file = event.target.files ? event.target.files[0] : null;
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.csv') && file.type && !file.type.includes('csv') && !file.type.includes('text')) {
        showToast('Vui lòng chọn file có định dạng CSV (.csv)', false);
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const csvText = e.target.result;
            processCsvImport(csvText, file.name);
        } catch (err) {
            console.error('Lỗi khi đọc file CSV:', err);
            showToast('Lỗi khi xử lý file CSV: ' + err.message, false);
        }
    };
    reader.onerror = function() {
        showToast('Không thể đọc file CSV. Vui lòng thử lại!', false);
    };
    reader.readAsText(file, 'utf-8');
}

/**
 * Parser RFC 4180 chuẩn hóa xử lý trường có dấu nháy kép, dấu phẩy và xuống dòng bên trong trường.
 */
function parseCSV(text) {
    const rows = [];
    let currentRow = [];
    let currentField = '';
    let inQuotes = false;
    const len = text.length;

    for (let i = 0; i < len; i++) {
        const char = text[i];
        const nextChar = (i + 1 < len) ? text[i + 1] : '';

        if (char === '"') {
            if (inQuotes && nextChar === '"') {
                currentField += '"';
                i++; // Skip the escaped quote
            } else {
                inQuotes = !inQuotes;
            }
        } else if (char === ',' && !inQuotes) {
            currentRow.push(currentField);
            currentField = '';
        } else if ((char === '\r' || char === '\n') && !inQuotes) {
            if (char === '\r' && nextChar === '\n') {
                i++;
            }
            currentRow.push(currentField);
            currentField = '';
            if (currentRow.length > 0 && (currentRow.length > 1 || currentRow[0].trim() !== '')) {
                rows.push(currentRow);
            }
            currentRow = [];
        } else {
            currentField += char;
        }
    }
    if (currentField || currentRow.length > 0) {
        currentRow.push(currentField);
        if (currentRow.length > 0 && (currentRow.length > 1 || currentRow[0].trim() !== '')) {
            rows.push(currentRow);
        }
    }
    return rows;
}

function processCsvImport(csvText, fileName) {
    const rows = parseCSV(csvText);
    if (!rows || rows.length < 2) {
        showToast('File CSV rỗng hoặc không có dữ liệu sản phẩm.', false);
        return;
    }

    const headers = rows[0].map(h => (h || '').trim());
    
    // Validate các cột bắt buộc tối thiểu của Shopify Product CSV
    const handleIdx = headers.indexOf('Handle');
    const titleIdx = headers.indexOf('Title');
    
    if (handleIdx === -1 || titleIdx === -1) {
        showToast('File CSV không đúng chuẩn Shopify Products Export (Thiếu cột "Handle" hoặc "Title")', false);
        return;
    }

    // Nhóm các dòng theo Handle
    const products = {};
    for (let i = 1; i < rows.length; i++) {
        const row = rows[i];
        if (!row || row.length === 0) continue;
        const rowDict = {};
        for (let j = 0; j < headers.length; j++) {
            rowDict[headers[j]] = (j < row.length) ? row[j] : '';
        }
        const handle = (rowDict['Handle'] || '').trim();
        if (!handle) continue;

        if (!products[handle]) {
            products[handle] = {
                handle: handle,
                firstRow: rowDict,
                rows: []
            };
        }
        // Nếu dòng hiện tại có Title mà firstRow chưa có Title thì cập nhật
        if (!products[handle].firstRow['Title'] && rowDict['Title']) {
            products[handle].firstRow['Title'] = rowDict['Title'];
        }
        products[handle].rows.push(rowDict);
    }

    const handles = Object.keys(products);
    if (handles.length === 0) {
        showToast('Không tìm thấy sản phẩm hợp lệ nào trong file CSV.', false);
        return;
    }

    parsedCsvProducts = products;

    if (handles.length === 1) {
        // Chỉ có 1 sản phẩm -> Điền trực tiếp vào form
        populateProductFromCsv(handles[0]);
    } else {
        // Có nhiều sản phẩm -> Mở modal cho người dùng chọn sản phẩm cần điền
        openCsvProductSelectModal(products, fileName);
    }
}

function openCsvProductSelectModal(products, fileName) {
    parsedCsvProducts = products || {};
    const modal = document.getElementById('csvProductSelectModal');
    const subtitleEl = document.getElementById('csv-modal-subtitle');
    
    const handles = Object.keys(products);
    // Mặc định chọn tất cả sản phẩm
    state.selectedCsvHandles = new Set(handles);

    if (subtitleEl) {
        subtitleEl.textContent = `File "${fileName || 'products_export.csv'}" có ${handles.length} sản phẩm. Tích chọn các sản phẩm bạn muốn tạo:`;
    }

    renderCsvProductsList(handles);
    updateCsvSelectionCount();

    if (modal) {
        modal.classList.remove('hidden');
    }
}

function renderCsvProductsList(handles) {
    const listEl = document.getElementById('csv-products-list');
    if (!listEl) return;

    listEl.innerHTML = handles.map((h, idx) => {
        const p = parsedCsvProducts[h];
        const title = p.firstRow['Title'] || h;
        const vendor = p.firstRow['Vendor'] || 'Wrydeco';
        const type = p.firstRow['Type'] || 'General';
        const category = p.firstRow['Product Category'] || 'Uncategorized';
        const rowCount = p.rows.length;
        const imgCount = p.rows.filter(r => r['Image Src'] && r['Image Src'].startsWith('http')).length;
        const isChecked = state.selectedCsvHandles.has(h);

        return `
            <div class="p-3.5 bg-white rounded-xl border ${isChecked ? 'border-indigo-400 bg-indigo-50/20' : 'border-gray-200'} hover:border-indigo-400 hover:shadow-xs transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3" id="csv-item-card-${escapeHtml(h)}">
                <div class="flex items-start gap-3 min-w-0 flex-1">
                    <div class="pt-1 shrink-0">
                        <input type="checkbox" 
                               id="csv-cb-${escapeHtml(h)}"
                               class="csv-product-checkbox w-5 h-5 rounded text-indigo-600 border-gray-300 focus:ring-indigo-500 cursor-pointer" 
                               data-handle="${escapeHtml(h)}"
                               ${isChecked ? 'checked' : ''}
                               onchange="toggleCsvProductSelection('${escapeHtml(h)}', this.checked)">
                    </div>
                    <div class="min-w-0 flex-1 cursor-pointer" onclick="toggleCsvProductFromCard('${escapeHtml(h)}')">
                        <div class="flex items-center gap-2 flex-wrap">
                            <h4 class="text-sm font-bold text-gray-900 truncate">${escapeHtml(title)}</h4>
                            <span class="px-2 py-0.5 text-sm font-mono rounded bg-gray-100 text-gray-600 border">${escapeHtml(h)}</span>
                        </div>
                        <p class="text-sm text-gray-500 mt-1 line-clamp-1">
                            <span class="font-semibold text-gray-700">Loại:</span> ${escapeHtml(type)} &bull; 
                            <span class="font-semibold text-gray-700">Vendor:</span> ${escapeHtml(vendor)} &bull;
                            <span class="font-semibold text-gray-700">Danh mục:</span> ${escapeHtml(category)}
                        </p>
                        <div class="flex items-center gap-2 mt-2">
                            <span class="px-2 py-0.5 text-sm font-semibold rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
                                ${rowCount} biến thể/dòng
                            </span>
                            <span class="px-2 py-0.5 text-sm font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                                ${imgCount} hình ảnh
                            </span>
                        </div>
                    </div>
                </div>
                <button type="button" onclick="handleSelectCsvProduct('${escapeHtml(h)}', this)" class="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 bg-gray-100 hover:bg-emerald-600 hover:text-white text-gray-700 text-sm font-bold rounded-xl transition-all shrink-0 cursor-pointer" title="Chỉ chọn riêng sản phẩm này và điền vào form">
                    <iconify-icon icon="mdi:form-select" class="text-base"></iconify-icon>
                    <span>Chỉ điền SP này</span>
                </button>
            </div>
        `;
    }).join('');
}

function toggleCsvProductFromCard(handle) {
    const cb = document.getElementById(`csv-cb-${handle}`);
    if (cb) {
        cb.checked = !cb.checked;
        toggleCsvProductSelection(handle, cb.checked);
    }
}

function toggleCsvProductSelection(handle, isChecked) {
    if (isChecked) {
        state.selectedCsvHandles.add(handle);
    } else {
        state.selectedCsvHandles.delete(handle);
    }
    const card = document.getElementById(`csv-item-card-${handle}`);
    if (card) {
        if (isChecked) {
            card.classList.add('border-indigo-400', 'bg-indigo-50/20');
            card.classList.remove('border-gray-200');
        } else {
            card.classList.remove('border-indigo-400', 'bg-indigo-50/20');
            card.classList.add('border-gray-200');
        }
    }
    updateCsvSelectionCount();
}

function selectAllCsvProducts() {
    const handles = Object.keys(parsedCsvProducts || {});
    state.selectedCsvHandles = new Set(handles);
    document.querySelectorAll('.csv-product-checkbox').forEach(cb => {
        cb.checked = true;
    });
    handles.forEach(h => {
        const card = document.getElementById(`csv-item-card-${h}`);
        if (card) {
            card.classList.add('border-indigo-400', 'bg-indigo-50/20');
            card.classList.remove('border-gray-200');
        }
    });
    updateCsvSelectionCount();
}

function deselectAllCsvProducts() {
    state.selectedCsvHandles.clear();
    document.querySelectorAll('.csv-product-checkbox').forEach(cb => {
        cb.checked = false;
    });
    Object.keys(parsedCsvProducts || {}).forEach(h => {
        const card = document.getElementById(`csv-item-card-${h}`);
        if (card) {
            card.classList.remove('border-indigo-400', 'bg-indigo-50/20');
            card.classList.add('border-gray-200');
        }
    });
    updateCsvSelectionCount();
}

function toggleSelectAllCsvProducts() {
    const total = Object.keys(parsedCsvProducts || {}).length;
    if (total > 0 && state.selectedCsvHandles.size === total) {
        deselectAllCsvProducts();
    } else {
        selectAllCsvProducts();
    }
}

function updateCsvSelectionCount() {
    const count = state.selectedCsvHandles.size;
    const total = Object.keys(parsedCsvProducts || {}).length;
    const badge = document.getElementById('csv-selection-badge');
    const btnCount = document.getElementById('csv-confirm-btn-count');
    const confirmBtn = document.getElementById('btn-confirm-csv-selection');
    const toggleBtnText = document.getElementById('toggle-select-all-text');
    const toggleBtnIcon = document.getElementById('toggle-select-all-icon');

    if (badge) badge.textContent = `Đã chọn: ${count} SP`;
    if (btnCount) btnCount.textContent = count;
    if (confirmBtn) {
        confirmBtn.disabled = count === 0;
        if (count === 0) {
            confirmBtn.classList.add('opacity-50', 'cursor-not-allowed');
        } else {
            confirmBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        }
    }

    const isAllSelected = total > 0 && count === total;
    if (toggleBtnText) {
        toggleBtnText.textContent = isAllSelected ? 'Bỏ chọn tất cả' : 'Chọn tất cả';
    }
    if (toggleBtnIcon) {
        toggleBtnIcon.setAttribute('icon', isAllSelected ? 'mdi:checkbox-blank-outline' : 'mdi:checkbox-multiple-marked');
    }
}

async function confirmCsvSelection() {
    const handles = Array.from(state.selectedCsvHandles);
    if (handles.length === 0) {
        showToast('Vui lòng chọn ít nhất 1 sản phẩm.', false);
        return;
    }

    if (handles.length === 1) {
        state.selectedBulkProducts = [];
        state.activeBulkProductId = null;
        updateFloatingBulkBadge();
        await populateProductFromCsv(handles[0]);
        closeCsvProductSelectModal();
        return;
    }

    // Nhiều hơn 1 sản phẩm: Chuẩn bị danh sách tạo hàng loạt
    state.selectedBulkProducts = handles.map(h => {
        const p = parsedCsvProducts[h];
        const payload = buildPayloadFromCsvProduct(p, h);
        return {
            clientId: 'bp_' + Math.random().toString(36).substring(2, 9),
            handle: h,
            title: p.firstRow['Title'] || h,
            descriptionHtml: p.firstRow['Body (HTML)'] || '',
            payload: payload,
            status: 'PENDING',
            error: null,
            links: null
        };
    });

    state.activeBulkProductId = state.selectedBulkProducts[0].clientId;

    // Hiển thị nút neo góc trên bên phải
    updateFloatingBulkBadge();

    // Đóng modal chọn CSV
    closeCsvProductSelectModal();

    // Điền sản phẩm đầu tiên vào form để xem trước/sửa
    await populateProductFromCsv(state.selectedBulkProducts[0].handle);

    // Thông báo cho người dùng
    Swal.fire({
        icon: 'success',
        title: 'Đã sẵn sàng tạo hàng loạt',
        html: `
            <div class="text-left text-sm text-gray-700 space-y-2">
                <p>Đã lưu <b>${state.selectedBulkProducts.length}</b> sản phẩm vào danh sách chờ tạo hàng loạt.</p>
                <p>Dữ liệu của sản phẩm đầu tiên (<b>${escapeHtml(state.selectedBulkProducts[0].title)}</b>) đã được nạp lên form để xem trước.</p>
                <p class="text-indigo-600 font-semibold mt-2">&bull; Nhấn vào nút neo <b>Gói hàng</b> ở góc trên bên phải màn hình bất cứ lúc nào để xem toàn bộ danh sách hoặc bấm "Bắt đầu tạo hàng loạt".</p>
            </div>
        `,
        confirmButtonText: 'Đã hiểu'
    });
}

function closeCsvProductSelectModal() {
    const modal = document.getElementById('csvProductSelectModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * Chuyển nút sang trạng thái spinner loading "Đang nạp dữ liệu..." ngay khi vừa click
 * để mang lại cảm giác phản hồi tức thì (Instant Feedback), sau đó nạp dữ liệu.
 */
async function handleSelectCsvProduct(handle, btnEl) {
    if (btnEl) {
        btnEl.disabled = true;
        btnEl.classList.remove('bg-emerald-600', 'hover:bg-emerald-700');
        btnEl.classList.add('bg-emerald-700', 'opacity-90', 'cursor-wait');
        btnEl.innerHTML = `
            <svg class="animate-spin -ml-0.5 mr-1.5 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>Đang nạp dữ liệu...</span>
        `;
    }
    // Cho trình duyệt 30ms render repaint trạng thái spinner ngay lập tức
    await new Promise(r => setTimeout(r, 30));
    try {
        state.selectedBulkProducts = [];
        state.activeBulkProductId = null;
        updateFloatingBulkBadge();
        await populateProductFromCsv(handle);
        closeCsvProductSelectModal();
    } finally {
        if (btnEl) {
            btnEl.disabled = false;
        }
    }
}

async function populateProductFromCsv(handle) {
    const product = parsedCsvProducts[handle];
    if (!product) {
        showToast('Không tìm thấy dữ liệu cho sản phẩm đã chọn.', false);
        return;
    }

    // Bật chế độ Batch Updating để gom tất cả cập nhật, chống lặp lại validation và DOM reflow
    isBatchUpdating = true;
    try {
        const firstRow = product.firstRow;
        const allRows = product.rows;

    // 1. Tiêu đề (Title)
    const titleVal = firstRow['Title'] || '';
    const titleInput = document.getElementById('product-title');
    if (titleInput) {
        titleInput.value = titleVal;
        handleTitleInput(titleVal);
    }

    // Handle (URL Slug) từ file CSV
    const csvHandle = handle || firstRow['Handle'] || '';
    const handleInput = document.getElementById('product-handle');
    if (handleInput && csvHandle) {
        handleInput.value = csvHandle;
        handleInput.setAttribute('data-touched', 'true');
        const resetBtn = document.getElementById('btn-reset-handle');
        if (resetBtn) resetBtn.classList.remove('hidden');
        const previewSpan = document.getElementById('seo-preview-handle');
        if (previewSpan) previewSpan.textContent = csvHandle;
    }

    // SEO Title & Description từ file CSV nếu có
    const csvSeoTitle = firstRow['SEO Title'] || '';
    const csvSeoDesc = firstRow['SEO Description'] || '';
    if (csvSeoTitle) {
        const seoTitleInput = document.getElementById('seo-title');
        if (seoTitleInput) {
            seoTitleInput.value = csvSeoTitle;
            handleSeoTitleInput(csvSeoTitle);
        }
    }
    if (csvSeoDesc) {
        const seoDescInput = document.getElementById('seo-desc');
        if (seoDescInput) {
            seoDescInput.value = csvSeoDesc;
            handleSeoDescInput(csvSeoDesc);
        }
    }

    // 2. Mô tả (Body HTML)
    const descVal = firstRow['Body (HTML)'] || '';
    const descInput = document.getElementById('product-desc');
    if (descInput) {
        descInput.value = descVal;
    }

    // 3. Loại sản phẩm (Type)
    const typeVal = firstRow['Type'] || '';
    const typeInput = document.getElementById('product-type');
    if (typeInput) {
        typeInput.value = typeVal;
    }

    // 4. Nhà cung cấp (Vendor)
    const vendorVal = firstRow['Vendor'] || 'Wrydeco';
    const vendorSelect = document.getElementById('product-vendor');
    if (vendorSelect) {
        let matched = false;
        for (let i = 0; i < vendorSelect.options.length; i++) {
            if (vendorSelect.options[i].value.toLowerCase() === vendorVal.toLowerCase()) {
                vendorSelect.selectedIndex = i;
                matched = true;
                break;
            }
        }
        if (!matched && vendorVal) {
            const opt = document.createElement('option');
            opt.value = vendorVal;
            opt.textContent = vendorVal;
            opt.selected = true;
            vendorSelect.appendChild(opt);
        }
    }

    // 5. Trạng thái (Status)
    const statusVal = (firstRow['Status'] || '').toLowerCase();
    const statusSelect = document.getElementById('product-status');
    if (statusSelect) {
        statusSelect.value = (statusVal === 'active') ? 'ACTIVE' : 'DRAFT';
    }

    // 6. Danh mục (Product Category / Taxonomy)
    const categoryVal = firstRow['Product Category'] || '';
    const catNameInput = document.getElementById('selected-category-name');
    const catIdInput = document.getElementById('selected-category-id');
    if (catNameInput && catIdInput) {
        catNameInput.value = categoryVal || 'Furniture > Shelving';
        state.selectedCategoryName = catNameInput.value;
        
        // Gán fallback ID ban đầu để form sẵn sàng ngay
        catIdInput.value = 'gid://shopify/TaxonomyCategory/hg-3-47';
        state.selectedCategoryId = catIdInput.value;

        // Chạy ngầm tra cứu taxonomy ID ở background mà KHÔNG dùng await chặn luồng chính
        try {
            const parts = categoryVal.split('>');
            const leafName = parts[parts.length - 1].trim() || 'Shelf';
            fetch(`/api/taxonomy?search=${encodeURIComponent(leafName)}`)
                .then(res => res.json())
                .then(taxData => {
                    if (taxData && taxData.nodes && taxData.nodes.length > 0) {
                        catIdInput.value = taxData.nodes[0].id;
                        state.selectedCategoryId = taxData.nodes[0].id;
                        updateValidationState();
                    }
                })
                .catch(err => {
                    console.warn("Background taxonomy fetch warning:", err);
                });
        } catch (e) {
            // silent catch
        }
    }

    // 7. Thẻ sản phẩm (Tags)
    const rawTags = firstRow['Tags'] || '';
    if (rawTags) {
        state.tags = rawTags.split(',').map(t => t.trim()).filter(Boolean);
        renderTags();
    }

    // 8. Phương tiện (Media / Image Src)
    const uniqueImages = [];
    allRows.forEach(r => {
        const src = (r['Image Src'] || '').trim();
        if (src && src.startsWith('http') && !uniqueImages.includes(src)) {
            uniqueImages.push(src);
        }
    });

    state.media = uniqueImages.map((src, idx) => ({
        id: 'med_' + Math.random().toString(36).substr(2, 9),
        kind: 'url',
        file: null,
        previewUrl: src,
        url: src,
        position: idx + 1
    }));
    renderMediaGallery();

    // 9. Biến thể (Options & Variant Matrix)
    // Thu thập Option Names & Values
    const detectedOptions = [];
    for (let optNum = 1; optNum <= 3; optNum++) {
        const optName = firstRow[`Option${optNum} Name`];
        if (optName && optName.trim()) {
            const uniqueVals = [];
            allRows.forEach(r => {
                const val = (r[`Option${optNum} Value`] || '').trim();
                if (val && !uniqueVals.includes(val)) {
                    uniqueVals.push(val);
                }
            });

            if (uniqueVals.length > 0) {
                detectedOptions.push({
                    name: optName.trim(),
                    values: uniqueVals
                });
            }
        }
    }

    // Nếu không có option nào hoặc chỉ có Title / Default Title
    if (detectedOptions.length === 0 || (detectedOptions.length === 1 && detectedOptions[0].name === 'Title' && detectedOptions[0].values.includes('Default Title'))) {
        state.options = [
            {
                clientId: 'opt_' + Math.random().toString(36).substr(2, 9),
                name: 'Color',
                isEditing: false,
                values: [
                    { clientId: 'val_' + Math.random().toString(36).substr(2, 9), label: 'Natural Oak' }
                ]
            }
        ];
        state.variantsByKey = {};
        const optValId = state.options[0].values[0].clientId;
        const p = parseFloat(firstRow['Variant Price']) || 129.00;
        let c = parseFloat(firstRow['Variant Compare At Price']) || 0;
        if (c <= p) c = Math.round(p * 1.25);

        state.variantsByKey[optValId] = {
            price: p.toFixed(2),
            compareAtPrice: c.toFixed(2),
            sku: firstRow['Variant SKU'] || `WRY-${handle.toUpperCase().slice(0, 8)}-1`,
            barcode: firstRow['Variant Barcodes'] || `8935${Date.now().toString().slice(-6)}01`
        };
    } else {
        // Thiết lập options
        state.options = detectedOptions.map(opt => ({
            clientId: 'opt_' + Math.random().toString(36).substr(2, 9),
            name: opt.name,
            isEditing: false,
            values: opt.values.map(val => ({
                clientId: 'val_' + Math.random().toString(36).substr(2, 9),
                label: val
            }))
        }));

        state.variantsByKey = {};

        // Duyệt từng dòng variant trong CSV để map chính xác giá và mã
        allRows.forEach((r, rowIdx) => {
            const rowVals = [];
            for (let i = 0; i < state.options.length; i++) {
                const optNum = i + 1;
                const vLabel = (r[`Option${optNum} Value`] || '').trim();
                const matchedVal = state.options[i].values.find(v => v.label.toLowerCase() === vLabel.toLowerCase());
                if (matchedVal) {
                    rowVals.push(matchedVal.clientId);
                }
            }

            if (rowVals.length === state.options.length) {
                const combKey = rowVals.join('_');
                const priceNum = parseFloat(r['Variant Price']) || 129.00;
                let compareNum = parseFloat(r['Variant Compare At Price']) || 0;
                
                // Quy tắc: Compare At Price phải > Price
                if (compareNum <= priceNum) {
                    compareNum = Math.round(priceNum * 1.25);
                }

                state.variantsByKey[combKey] = {
                    price: priceNum.toFixed(2),
                    compareAtPrice: compareNum.toFixed(2),
                    sku: r['Variant SKU'] || `WRY-${handle.toUpperCase().slice(0, 8)}-${rowIdx + 1}`,
                    barcode: r['Variant Barcodes'] || `8935${Date.now().toString().slice(-6)}${String(rowIdx + 1).padStart(2, '0')}`
                };
            }
        });
    }

    renderOptions();
    rebuildVariantMatrix();

    // 10. Phong cách nội thất (Interior Style)
    let styleStr = '';
    for (const k in firstRow) {
        if (k.includes('interior_style')) {
            styleStr = firstRow[k];
            break;
        }
    }
    const styleCheckboxes = document.querySelectorAll('input[name="interior_style"]');
    let anyStyleChecked = false;
    styleCheckboxes.forEach(cb => {
        if (styleStr && styleStr.toLowerCase().includes(cb.value.toLowerCase())) {
            cb.checked = true;
            anyStyleChecked = true;
        } else {
            cb.checked = false;
        }
    });
    if (!anyStyleChecked && styleCheckboxes.length > 0) {
        styleCheckboxes[0].checked = true;
    }

    // 11. Không gian phòng (Room Type)
    let roomStr = '';
    for (const k in firstRow) {
        if (k.includes('room_type')) {
            roomStr = firstRow[k];
            break;
        }
    }
    const roomCheckboxes = document.querySelectorAll('input[name="room_type"]');
    let anyRoomChecked = false;
    roomCheckboxes.forEach(cb => {
        if (roomStr && roomStr.toLowerCase().includes(cb.value.toLowerCase())) {
            cb.checked = true;
            anyRoomChecked = true;
        } else {
            cb.checked = false;
        }
    });
    if (!anyRoomChecked && roomCheckboxes.length > 0) {
        roomCheckboxes[0].checked = true;
    }

    // 12. Tác giả thiết kế (Author)
    let authorVal = '';
    for (const k in firstRow) {
        if (k.includes('author_info')) {
            authorVal = firstRow[k];
            break;
        }
    }
    if (state.authors && state.authors.length > 0) {
        let matchedAuthor = null;
        if (authorVal) {
            const cleanAuthor = authorVal.toLowerCase().replace(/[^a-z0-9]/g, '');
            matchedAuthor = state.authors.find(a => {
                const aHandle = (a.handle || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                const aName = (a.name || a.displayName || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                return aHandle.includes(cleanAuthor) || cleanAuthor.includes(aHandle) || aName.includes(cleanAuthor);
            });
        }
        if (!matchedAuthor) {
            matchedAuthor = state.authors[0];
        }
        if (matchedAuthor) {
            selectInlineAuthor(matchedAuthor.id);
        }
    }

    // 13. Mô tả mở rộng (Rich Description)
    let richDescVal = '';
    for (const k in firstRow) {
        if (k.includes('rich_description')) {
            richDescVal = firstRow[k];
            break;
        }
    }
    const richDescInput = document.getElementById('rich-description');
    if (richDescInput) {
        richDescInput.value = richDescVal || `<div class="rich-desc"><p>Khám phá mẫu thiết kế ${escapeHtml(titleVal)} chế tác từ gỗ tự nhiên độc bản WRYDECO.</p></div>`;
    }

    // 14. Nội dung AEO (Answer Engine Optimization)
    let aeoVal = '';
    for (const k in firstRow) {
        if (k.includes('aeo_html')) {
            aeoVal = firstRow[k];
            break;
        }
    }
    const aeoInput = document.getElementById('aeo-html');
    if (aeoInput) {
        aeoInput.value = aeoVal || `<div><p>Sản phẩm <strong>${escapeHtml(titleVal)}</strong> của thương hiệu WRYDECO được chế tác thủ công tinh xảo, tối ưu hóa cho không gian nội thất hiện đại.</p></div>`;
    }

    // 15. Tối ưu hóa tìm kiếm (SEO Title & SEO Description)
    const seoTitleVal = firstRow['SEO Title'] || (titleVal ? `${titleVal} | Wrydeco` : '');
    const seoDescVal = firstRow['SEO Description'] || `Khám phá ${titleVal} chất lượng cao từ Wrydeco. Thiết kế sang trọng, độ bền vượt trội. Mua ngay!`;
    
    const seoTitleInput = document.getElementById('seo-title');
    if (seoTitleInput) {
        seoTitleInput.value = seoTitleVal;
        handleSeoTitleInput(seoTitleVal);
    }
    const seoDescInput = document.getElementById('seo-desc');
    if (seoDescInput) {
        seoDescInput.value = seoDescVal;
        handleSeoDescInput(seoDescVal);
    }

    // Đóng modal chọn sản phẩm nếu đang mở
    closeCsvProductSelectModal();

    // Cuộn mượt lên đầu trang
    window.scrollTo({ top: 0, behavior: 'smooth' });

    showToast(`Đã import và điền toàn bộ dữ liệu sản phẩm "${titleVal || handle}" từ file CSV thành công!`, true);
    } finally {
        // Tắt chế độ Batch Updating và kích hoạt validation duy nhất 1 lần
        isBatchUpdating = false;
        updateValidationState();
    }
}

/**
 * Hiển thị Toast thông báo trạng thái bằng thư viện SweetAlert2
 */
function showToast(message, isSuccess = true) {
    if (typeof Swal !== 'undefined') {
        const Toast = Swal.mixin({
            toast: true,
            position: 'bottom-end',
            showConfirmButton: false,
            timer: 4000,
            timerProgressBar: true,
            didOpen: (toast) => {
                toast.onmouseenter = Swal.stopTimer;
                toast.onmouseleave = Swal.resumeTimer;
            }
        });

        Toast.fire({
            icon: isSuccess ? 'success' : 'error',
            title: message,
            customClass: {
                popup: '!mb-24 !mr-6 !rounded-2xl !shadow-2xl !border !border-gray-200 !text-sm !font-semibold'
            }
        });
        return;
    }

    // Fallback UI thông báo nếu SweetAlert2 chưa sẵn sàng
    const toast = document.getElementById('toastNotification');
    const toastBox = document.getElementById('toastBox');
    const toastIcon = document.getElementById('toastIcon');
    const toastMsg = document.getElementById('toastMessage');
    
    if (!toast || !toastBox || !toastMsg) {
        alert(message);
        return;
    }

    toastMsg.textContent = message;
    if (isSuccess) {
        toastBox.className = 'flex items-center gap-3 px-5 py-3.5 rounded-2xl shadow-xl text-sm font-bold border border-emerald-300 bg-emerald-50 text-emerald-900';
        if (toastIcon) {
            toastIcon.className = 'text-2xl text-emerald-600';
            toastIcon.setAttribute('icon', 'mdi:check-circle');
        }
    } else {
        toastBox.className = 'flex items-center gap-3 px-5 py-3.5 rounded-2xl shadow-xl text-sm font-bold border border-red-300 bg-red-50 text-red-900';
        if (toastIcon) {
            toastIcon.className = 'text-2xl text-red-600';
            toastIcon.setAttribute('icon', 'mdi:alert-circle');
        }
    }

    toast.classList.remove('hidden');
    clearTimeout(window._toastTimeout);
    window._toastTimeout = setTimeout(() => {
        toast.classList.add('hidden');
    }, 4500);
}

// ==========================================
// BACKDROP & KEYBOARD SAFE CLOSE HANDLERS
// ==========================================
let isCsvBackdropMousedown = false;
function handleCsvBackdropMouseDown(e) {
    isCsvBackdropMousedown = (e.target === e.currentTarget);
}

function handleCsvBackdropClick(e) {
    if (isCsvBackdropMousedown && e.target === e.currentTarget) {
        closeCsvProductSelectModal();
    }
    isCsvBackdropMousedown = false;
}

let isCatBackdropMousedown = false;
function handleCatBackdropMouseDown(e) {
    isCatBackdropMousedown = (e.target === e.currentTarget);
}

function handleCatBackdropClick(e) {
    if (isCatBackdropMousedown && e.target === e.currentTarget) {
        closeCategoryModal();
    }
    isCatBackdropMousedown = false;
}

let isBulkOverviewBackdropMousedown = false;
function handleBulkOverviewBackdropMouseDown(e) {
    isBulkOverviewBackdropMousedown = (e.target === e.currentTarget);
}

function handleBulkOverviewBackdropClick(e) {
    if ((isBulkOverviewBackdropMousedown || e.target === document.getElementById('bulkProductsOverviewModal')) && e.target === e.currentTarget) {
        closeBulkOverviewModal();
    }
    isBulkOverviewBackdropMousedown = false;
}

// Đóng modal khi bấm Escape
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const csvModal = document.getElementById('csvProductSelectModal');
        if (csvModal && !csvModal.classList.contains('hidden')) {
            closeCsvProductSelectModal();
        }
        const catModal = document.getElementById('category-modal');
        if (catModal && !catModal.classList.contains('hidden')) {
            closeCategoryModal();
        }
        const bulkOverviewModal = document.getElementById('bulkProductsOverviewModal');
        if (bulkOverviewModal && !bulkOverviewModal.classList.contains('hidden')) {
            closeBulkOverviewModal();
        }
    }
});


// ==========================================
// 12. POST-CREATION SUCCESS ACTIONS CONTROLLER
// ==========================================
let lastCreatedProductData = null;

function showCreatedProductSuccessSection(productData, storeType) {
    lastCreatedProductData = {
        ...productData,
        storeType: storeType || state.currentStoreType || 'default'
    };

    const section = document.getElementById('create-success-actions-section');
    if (!section) return;

    // Điền thông tin
    const titleEl = document.getElementById('created-product-title-display');
    const handleEl = document.getElementById('created-product-handle-display');
    const idEl = document.getElementById('created-product-id-display');
    const storeBadge = document.getElementById('created-store-badge');

    const rawId = String(productData.id || '');
    const numId = rawId.includes('/') ? rawId.split('/').pop() : rawId;
    const handle = productData.handle || (document.getElementById('product-handle')?.value || '').trim();
    const title = productData.title || (document.getElementById('product-title')?.value || '').trim();

    if (titleEl) titleEl.textContent = title || 'Sản phẩm mới';
    if (handleEl) handleEl.textContent = handle || 'N/A';
    if (idEl) idEl.textContent = numId || 'N/A';
    
    if (storeBadge) {
        if (storeType === 'custom') {
            storeBadge.className = 'px-2.5 py-0.5 rounded-full text-sm font-bold bg-teal-100 text-teal-800 border border-teal-300';
            storeBadge.textContent = 'Store Riêng (qua Proxy US)';
        } else {
            storeBadge.className = 'px-2.5 py-0.5 rounded-full text-sm font-bold bg-indigo-100 text-indigo-800 border border-indigo-200';
            storeBadge.textContent = 'Store Mặc định';
        }
    }

    // Hiển thị section và cuộn lên
    section.classList.remove('hidden');
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Toast chúc mừng
    if (typeof Swal !== 'undefined') {
        const Toast = Swal.mixin({
            toast: true,
            position: 'bottom-end',
            showConfirmButton: false,
            timer: 5000,
            timerProgressBar: true
        });
        Toast.fire({
            icon: 'success',
            title: `Tạo thành công sản phẩm "${title}"! Hãy chọn hành động bên dưới.`
        });
    }
}

async function handleSuccessAction(actionType) {
    if (!lastCreatedProductData) {
        showToast('Không tìm thấy thông tin sản phẩm vừa tạo.', false);
        return;
    }

    const { id, handle, title, storeType } = lastCreatedProductData;
    const rawId = String(id || '');
    const numId = rawId.includes('/') ? rawId.split('/').pop() : rawId;
    const effectiveStore = storeType || state.currentStoreType || 'default';

    if (actionType === 'tool') {
        // Nút 1: Đi đến trang sản phẩm trong tool này
        const toolUrl = `/product/${encodeURIComponent(handle)}?store_type=${effectiveStore}`;
        window.open(toolUrl, '_blank');
        return;
    }

    if (actionType === 'shopify') {
        // Nút 3: Đi đến trang sản phẩm trong Shopify Admin
        const adminShop = (effectiveStore === 'custom') ? '236qm8-w7' : 'wrydeco';
        const adminUrl = numId ? `https://admin.shopify.com/store/${adminShop}/products/${numId}` : `https://admin.shopify.com/store/${adminShop}/products`;
        window.open(adminUrl, '_blank');
        return;
    }

    if (actionType === 'default-store') {
        // Nút 4: Đi đến trên Wrydeco store website (Store mặc định)
        const webUrl = `https://wrydeco.com/products/${encodeURIComponent(handle)}`;
        window.open(webUrl, '_blank');
        return;
    }

    if (actionType === 'custom-store') {
        // Nút 5: Đi đến trên Wrydeco store website (Store riêng)
        const customUrl = `https://236qm8-w7.myshopify.com/products/${encodeURIComponent(handle)}`;
        window.open(customUrl, '_blank');
        return;
    }

    if (actionType === 'amazon') {
        // Nút 2: Đi đến trang sản phẩm trên Amazon (tham khảo logic từ index.html)
        const btn = document.getElementById('btn-action-amazon');
        const origHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `
                <svg class="animate-spin w-5 h-5 text-current shrink-0" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Đang kiểm tra...</span>
            `;
        }

        try {
            const resp = await fetch(`/api/products/resolve-links?query=${encodeURIComponent(handle)}&store_type=${effectiveStore}`);
            const data = await resp.json();
            if (data.success && data.product && data.product.amazon_link) {
                window.open(data.product.amazon_link, '_blank');
            } else {
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'info',
                        title: 'Chưa có liên kết Amazon',
                        text: `Sản phẩm "${title || handle}" chưa được gắn trường liên kết Amazon (metafield custom.amazon_link).`,
                        confirmButtonText: 'Đã hiểu',
                        confirmButtonColor: '#f59e0b'
                    });
                } else {
                    alert(`Sản phẩm "${title || handle}" chưa được gắn liên kết Amazon.`);
                }
            }
        } catch (e) {
            showToast('Lỗi khi tra cứu liên kết Amazon: ' + e.message, false);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = origHtml;
            }
        }
    }
}

function resetFormForNewProduct() {
    window.location.reload();
}


// =============================================================================
// QUẢN LÝ TẠO SẢN PHẨM HÀNG LOẠT (BULK PRODUCT CREATION VIA CSV)
// =============================================================================

/**
 * Trích xuất payload từ sản phẩm CSV thô để chuẩn bị đưa vào Bulk Job
 */
function buildPayloadFromCsvProduct(product, handle) {
    if (!product || !product.firstRow) return null;
    const firstRow = product.firstRow;
    const allRows = product.rows || [firstRow];

    const title = firstRow['Title'] || handle;
    const h = handle || firstRow['Handle'] || '';
    const desc = firstRow['Body (HTML)'] || '';
    const productType = firstRow['Type'] || 'Furniture';
    const categoryId = firstRow['Product Category ID'] || 'gid://shopify/TaxonomyCategory/hg-3-47';
    const statusVal = (firstRow['Status'] || '').toLowerCase();
    const status = (statusVal === 'active') ? 'ACTIVE' : 'DRAFT';
    const vendor = firstRow['Vendor'] || 'Wrydeco';
    const rawTags = firstRow['Tags'] || '';
    const tags = rawTags ? rawTags.split(',').map(t => t.trim()).filter(Boolean) : [];

    const seoTitle = firstRow['SEO Title'] || (title ? `${title} | Wrydeco` : '');
    const seoDesc = firstRow['SEO Description'] || (title ? `Khám phá ${title} chất lượng cao từ Wrydeco. Thiết kế sang trọng, độ bền vượt trội.` : '');

    // Default author from state if available
    let authorId = state.authors && state.authors.length > 0 ? state.authors[0].id : 'gid://shopify/Metaobject/default-author';
    let authorVal = '';
    for (const k in firstRow) {
        if (k.includes('author_info')) {
            authorVal = firstRow[k];
            break;
        }
    }
    if (authorVal && state.authors && state.authors.length > 0) {
        const cleanAuthor = authorVal.toLowerCase().replace(/[^a-z0-9]/g, '');
        const matched = state.authors.find(a => {
            const aHandle = (a.handle || '').toLowerCase().replace(/[^a-z0-9]/g, '');
            const aName = (a.name || a.displayName || '').toLowerCase().replace(/[^a-z0-9]/g, '');
            return aHandle.includes(cleanAuthor) || cleanAuthor.includes(aHandle) || aName.includes(cleanAuthor);
        });
        if (matched) authorId = matched.id;
    }

    // Rich desc & AEO
    let richDesc = '';
    for (const k in firstRow) {
        if (k.includes('rich_description')) {
            richDesc = firstRow[k];
            break;
        }
    }
    if (!richDesc) {
        richDesc = `<div class="rich-desc"><p>Khám phá mẫu thiết kế ${escapeHtml(title)} chế tác từ gỗ tự nhiên độc bản WRYDECO.</p></div>`;
    }

    let aeoHtml = '';
    for (const k in firstRow) {
        if (k.includes('aeo_html')) {
            aeoHtml = firstRow[k];
            break;
        }
    }
    if (!aeoHtml) {
        aeoHtml = `<div><p>Sản phẩm <strong>${escapeHtml(title)}</strong> của thương hiệu WRYDECO được chế tác thủ công tinh xảo, tối ưu hóa cho không gian nội thất hiện đại.</p></div>`;
    }

    // Interior style
    let interiorStyle = [];
    let styleStr = '';
    for (const k in firstRow) {
        if (k.includes('interior_style')) {
            styleStr = firstRow[k];
            break;
        }
    }
    const standardInteriorStyles = ['Rustic', 'Japandi', 'Mid-Century', 'Organic Modern'];
    standardInteriorStyles.forEach(st => {
        if (styleStr && styleStr.toLowerCase().includes(st.toLowerCase())) {
            interiorStyle.push(st);
        }
    });
    if (interiorStyle.length === 0) interiorStyle = ['Rustic'];

    // Room type
    let roomType = [];
    let roomStr = '';
    for (const k in firstRow) {
        if (k.includes('room_type')) {
            roomStr = firstRow[k];
            break;
        }
    }
    const standardRoomTypes = [
        'Living Room', 
        'Bedroom', 
        'Kitchen & Dining', 
        'Home Office & Library', 
        'Nursery & Kids\' Room', 
        'Entryway & Hallway', 
        'Bathroom'
    ];
    standardRoomTypes.forEach(rm => {
        const keyword = rm.split('&')[0].trim().toLowerCase();
        if (roomStr && (roomStr.toLowerCase().includes(rm.toLowerCase()) || roomStr.toLowerCase().includes(keyword))) {
            roomType.push(rm);
        }
    });
    if (roomType.length === 0) roomType = ['Living Room'];

    // Media
    const uniqueImages = [];
    allRows.forEach(r => {
        const src = (r['Image Src'] || '').trim();
        if (src && src.startsWith('http') && !uniqueImages.includes(src)) {
            uniqueImages.push(src);
        }
    });
    const media = uniqueImages.map((src, idx) => ({
        kind: 'url',
        url: src,
        position: idx + 1
    }));

    // Options & Variants
    const detectedOptions = [];
    for (let optNum = 1; optNum <= 3; optNum++) {
        const optName = firstRow[`Option${optNum} Name`];
        if (optName && optName.trim()) {
            const uniqueVals = [];
            allRows.forEach(r => {
                const val = (r[`Option${optNum} Value`] || '').trim();
                if (val && !uniqueVals.includes(val)) {
                    uniqueVals.push(val);
                }
            });
            if (uniqueVals.length > 0) {
                detectedOptions.push({
                    name: optName.trim(),
                    values: uniqueVals
                });
            }
        }
    }

    let optionsPayload = [];
    let variantsPayload = [];

    if (detectedOptions.length === 0 || (detectedOptions.length === 1 && detectedOptions[0].name === 'Title' && detectedOptions[0].values.includes('Default Title'))) {
        optionsPayload = [{ name: 'Color', values: [{ label: 'Natural Oak' }] }];
        const p = parseFloat(firstRow['Variant Price']) || 129.00;
        let c = parseFloat(firstRow['Variant Compare At Price']) || 0;
        if (c <= p) c = Math.round(p * 1.25);
        variantsPayload = [{
            optionValues: [{ optionName: 'Color', name: 'Natural Oak' }],
            price: p.toFixed(2),
            compareAtPrice: c.toFixed(2),
            sku: firstRow['Variant SKU'] || `WRY-${h.toUpperCase().slice(0, 8)}-1`,
            barcode: firstRow['Variant Barcodes'] || `8935${Date.now().toString().slice(-6)}01`
        }];
    } else {
        optionsPayload = detectedOptions.map(opt => ({
            name: opt.name,
            values: opt.values.map(val => ({ label: val }))
        }));

        variantsPayload = allRows.map((r, rowIdx) => {
            const optVals = [];
            for (let i = 0; i < detectedOptions.length; i++) {
                const optNum = i + 1;
                const vLabel = (r[`Option${optNum} Value`] || '').trim();
                optVals.push({
                    optionName: detectedOptions[i].name,
                    name: vLabel || detectedOptions[i].values[0]
                });
            }

            const pNum = parseFloat(r['Variant Price']) || 129.00;
            let cNum = parseFloat(r['Variant Compare At Price']) || 0;
            if (cNum <= pNum) cNum = Math.round(pNum * 1.25);

            return {
                optionValues: optVals,
                price: pNum.toFixed(2),
                compareAtPrice: cNum.toFixed(2),
                sku: r['Variant SKU'] || `WRY-${h.toUpperCase().slice(0, 8)}-${rowIdx + 1}`,
                barcode: r['Variant Barcodes'] || `8935${Date.now().toString().slice(-6)}${String(rowIdx + 1).padStart(2, '0')}`
            };
        });
    }

    return {
        store_type: state.currentStoreType,
        title,
        handle: h,
        descriptionHtml: desc,
        productType,
        categoryId,
        status,
        vendor,
        tags,
        seo: {
            title: seoTitle,
            description: seoDesc
        },
        authorId,
        richDescription: richDesc,
        aeoHtml,
        interiorStyle,
        roomType,
        options: optionsPayload,
        variants: variantsPayload,
        media
    };
}

/**
 * Trích xuất toàn bộ dữ liệu hiện tại trên form thành payload chuẩn
 */
function collectCurrentFormPayload() {
    const title = (document.getElementById('product-title')?.value || '').trim();
    const handle = (document.getElementById('product-handle')?.value || '').trim();
    const desc = (document.getElementById('product-desc')?.value || '').trim();
    const productType = (document.getElementById('product-type')?.value || '').trim();
    const categoryId = (document.getElementById('selected-category-id')?.value || state.selectedCategoryId || '').trim();
    const status = document.getElementById('product-status')?.value || 'DRAFT';
    const vendor = document.getElementById('product-vendor')?.value || 'Wrydeco';
    const seoTitle = (document.getElementById('seo-title')?.value || '').trim();
    const seoDesc = (document.getElementById('seo-desc')?.value || '').trim();
    const authorId = (document.getElementById('selected-author-id')?.value || state.selectedAuthorId || '').trim();
    const richDesc = (document.getElementById('rich-description')?.value || '').trim();
    const aeoHtml = (document.getElementById('aeo-html')?.value || '').trim();

    const checkedInterior = Array.from(document.querySelectorAll('input[name="interior_style"]:checked')).map(cb => cb.value);
    const checkedRoom = Array.from(document.querySelectorAll('input[name="room_type"]:checked')).map(cb => cb.value);

    // Variants list mapping
    const validOptions = state.options.filter(o => o.name.trim() && o.values.length > 0);
    const optionArrays = validOptions.map(o => o.values.map(v => ({
        optionName: o.name,
        valueId: v.clientId,
        valueLabel: v.label
    })));

    const combs = optionArrays.reduce((acc, curr) => {
        const res = [];
        acc.forEach(a => curr.forEach(c => res.push([...a, c])));
        return res;
    }, [[]]);

    const variantsPayload = combs.map(comb => {
        const combKey = comb.map(c => c.valueId).join('_');
        const row = state.variantsByKey[combKey] || {};
        return {
            optionValues: comb.map(c => ({
                optionName: c.optionName,
                name: c.valueLabel
            })),
            price: row.price || "129.00",
            compareAtPrice: row.compareAtPrice || "160.00",
            sku: row.sku || `WRY-${handle.toUpperCase().slice(0, 8)}-1`,
            barcode: row.barcode || `8935${Date.now().toString().slice(-6)}01`
        };
    });

    const optionsPayload = validOptions.map(o => ({
        name: o.name,
        values: o.values.map(v => ({ label: v.label }))
    }));

    const mediaMetadata = [];
    state.media.forEach((m, idx) => {
        if (m.kind === 'url') {
            mediaMetadata.push({
                kind: 'url',
                url: m.url,
                position: idx + 1
            });
        }
    });

    return {
        store_type: state.currentStoreType,
        title,
        handle,
        descriptionHtml: desc,
        productType: productType || 'Furniture',
        categoryId: categoryId || 'gid://shopify/TaxonomyCategory/hg-3-47',
        status,
        vendor: vendor || 'Wrydeco',
        tags: state.tags || [],
        seo: {
            title: seoTitle || (title ? `${title} | Wrydeco` : ''),
            description: seoDesc || (title ? `Khám phá ${title} chất lượng cao từ Wrydeco.` : '')
        },
        authorId: authorId || (state.authors && state.authors.length > 0 ? state.authors[0].id : 'gid://shopify/Metaobject/default-author'),
        richDescription: richDesc,
        aeoHtml: aeoHtml,
        interiorStyle: checkedInterior.length > 0 ? checkedInterior : ['Rustic'],
        roomType: checkedRoom.length > 0 ? checkedRoom : ['Living Room'],
        options: optionsPayload,
        variants: variantsPayload,
        media: mediaMetadata
    };
}

/**
 * Lưu dữ liệu đang chỉnh sửa trên form vào item tương ứng trong danh sách hàng loạt
 */
function flushActiveProductFormToState() {
    if (!state.activeBulkProductId || !state.selectedBulkProducts || state.selectedBulkProducts.length === 0) {
        return;
    }
    const currentItem = state.selectedBulkProducts.find(item => item.clientId === state.activeBulkProductId);
    if (currentItem) {
        const payload = collectCurrentFormPayload();
        currentItem.payload = payload;
        currentItem.title = payload.title || currentItem.title;
        currentItem.handle = payload.handle || currentItem.handle;
    }
}

/**
 * Cập nhật nút neo góc trên bên phải (Badge) và số lượng sản phẩm trên nút tạo
 */
function updateFloatingBulkBadge() {
    const container = document.getElementById('floating-bulk-container');
    const countEl = document.getElementById('bulk-anchor-count') || document.getElementById('floating-bulk-count');

    const count = (state.selectedBulkProducts || []).length;
    if (container && countEl) {
        if (count > 0) {
            countEl.textContent = count;
            container.classList.remove('hidden');
        } else {
            container.classList.add('hidden');
        }
    }
    updateSubmitButtonLabel();
}

/**
 * Cập nhật nhãn nút tạo sản phẩm: "Tiến hành tạo {số lượng} sản phẩm"
 */
function updateSubmitButtonLabel() {
    const btnText = document.getElementById('submit-btn-text');
    if (!btnText || state.isSubmitting) return;

    const bulkCount = (state.selectedBulkProducts || []).length;
    const count = bulkCount > 0 ? bulkCount : 1;
    btnText.textContent = `Tiến hành tạo ${count} sản phẩm`;
}

/**
 * Mở modal tổng quan danh sách sản phẩm hàng loạt dạng bảng
 */
function openBulkOverviewModal() {
    flushActiveProductFormToState();

    const modal = document.getElementById('bulkProductsOverviewModal');
    const tbody = document.getElementById('bulk-overview-table-body');
    const countEl = document.getElementById('bulk-overview-count');
    const startBtnCount = document.getElementById('bulk-start-btn-count');
    if (!modal) return;

    const items = state.selectedBulkProducts || [];
    if (countEl) countEl.textContent = items.length;
    if (startBtnCount) startBtnCount.textContent = items.length;

    if (tbody) {
        if (items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="px-4 py-8 text-center text-sm text-gray-500">Chưa có sản phẩm nào trong danh sách.</td></tr>`;
        } else {
            tbody.innerHTML = items.map((item, idx) => {
                const p = item.payload || {};
                const seo = p.seo || {};
                const isActive = item.clientId === state.activeBulkProductId;
                const variantCount = (p.variants || []).length || 1;
                const statusBadge = item.status === 'SUCCESS' 
                    ? '<span class="px-2.5 py-0.5 rounded-full text-sm font-semibold bg-emerald-100 text-emerald-800">Thành công</span>'
                    : item.status === 'ERROR'
                    ? `<span class="px-2.5 py-0.5 rounded-full text-sm font-semibold bg-red-100 text-red-800" title="${escapeHtml(item.error || '')}">Lỗi</span>`
                    : item.status === 'RUNNING'
                    ? '<span class="px-2.5 py-0.5 rounded-full text-sm font-semibold bg-blue-100 text-blue-800 animate-pulse">Đang tạo...</span>'
                    : '<span class="px-2.5 py-0.5 rounded-full text-sm font-semibold bg-gray-100 text-gray-700">Chờ tạo</span>';

                const cleanDesc = (p.descriptionHtml || '').replace(/<[^>]*>?/gm, ' ').trim();
                const descSnippet = cleanDesc ? (cleanDesc.length > 60 ? cleanDesc.slice(0, 60) + '...' : cleanDesc) : '—';
                const seoSnippet = (seo.title || p.title || '') + (seo.description ? ` | ${seo.description.slice(0, 40)}...` : '');

                return `
                    <tr class="hover:bg-gray-50/80 transition-colors ${isActive ? 'bg-indigo-50/40 border-l-4 border-l-indigo-600' : ''}">
                        <td class="px-3.5 py-3 text-sm font-semibold text-gray-700 text-center">${idx + 1}</td>
                        <td class="px-3.5 py-3 text-sm">
                            <div class="flex items-center gap-1.5 flex-nowrap">
                                <button type="button" 
                                        onclick="switchToBulkProductPreview('${item.clientId}')" 
                                        class="inline-flex items-center gap-1 px-2.5 py-1 text-sm font-bold rounded-lg ${isActive ? 'bg-indigo-600 text-white shadow-xs' : 'bg-gray-100 hover:bg-indigo-50 hover:text-indigo-600 text-gray-700'} transition-all cursor-pointer"
                                        title="Xem và chỉnh sửa chi tiết trên form">
                                    <iconify-icon icon="${isActive ? 'mdi:eye-check' : 'mdi:eye-outline'}" class="text-base"></iconify-icon>
                                    <span>${isActive ? 'Đang xem' : 'Xem form'}</span>
                                </button>
                                <button type="button" 
                                        onclick="removeBulkProduct('${item.clientId}')" 
                                        class="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors cursor-pointer"
                                        title="Gỡ sản phẩm khỏi danh sách tạo hàng loạt">
                                    <iconify-icon icon="mdi:trash-can-outline" class="text-base"></iconify-icon>
                                </button>
                            </div>
                        </td>
                        <td class="px-3.5 py-3 text-sm font-mono text-gray-600 font-semibold truncate max-w-[160px]" title="${escapeHtml(item.handle || '')}">${escapeHtml(item.handle || '—')}</td>
                        <td class="px-3.5 py-3 text-sm font-bold text-gray-900 truncate max-w-[200px]" title="${escapeHtml(item.title || '')}">${escapeHtml(item.title || '—')}</td>
                        <td class="px-3.5 py-3 text-sm text-gray-500 truncate max-w-[180px]" title="${escapeHtml(cleanDesc)}">${escapeHtml(descSnippet)}</td>
                        <td class="px-3.5 py-3 text-sm text-gray-500 truncate max-w-[180px]" title="${escapeHtml(seoSnippet)}">${escapeHtml(seoSnippet || '—')}</td>
                        <td class="px-3.5 py-3 text-sm text-center font-semibold text-gray-700">${variantCount}</td>
                        <td class="px-3.5 py-3 text-sm text-center whitespace-nowrap">${statusBadge}</td>
                    </tr>
                `;
            }).join('');
        }
    }

    modal.classList.remove('hidden');
}

/**
 * Đóng modal tổng quan danh sách sản phẩm hàng loạt
 */
function closeBulkOverviewModal() {
    const modal = document.getElementById('bulkProductsOverviewModal');
    if (modal) modal.classList.add('hidden');
}

/**
 * Chuyển đổi sản phẩm được xem trước và chỉnh sửa trên form
 */
async function switchToBulkProductPreview(clientId) {
    if (clientId === state.activeBulkProductId) {
        closeBulkOverviewModal();
        return;
    }
    // Flush dữ liệu form hiện tại vào item cũ
    flushActiveProductFormToState();

    const targetItem = state.selectedBulkProducts.find(i => i.clientId === clientId);
    if (!targetItem) return;

    state.activeBulkProductId = clientId;

    // Nạp sản phẩm đích lên form
    await populateProductFromCsv(targetItem.handle);

    closeBulkOverviewModal();
    showToast(`Đang xem trước và chỉnh sửa: "${targetItem.title || targetItem.handle}"`, true);
}

/**
 * Gỡ một sản phẩm khỏi danh sách tạo hàng loạt
 */
function removeBulkProduct(clientId) {
    const idx = state.selectedBulkProducts.findIndex(i => i.clientId === clientId);
    if (idx < 0) return;

    state.selectedBulkProducts.splice(idx, 1);
    if (state.activeBulkProductId === clientId) {
        if (state.selectedBulkProducts.length > 0) {
            state.activeBulkProductId = state.selectedBulkProducts[0].clientId;
            populateProductFromCsv(state.selectedBulkProducts[0].handle);
        } else {
            state.activeBulkProductId = null;
        }
    }
    updateFloatingBulkBadge();
    openBulkOverviewModal();
}

/**
 * Bắt đầu tiến trình tạo hàng loạt (Bulk Creation Workflow)
 */
async function startBulkCreationWorkflow() {
    if (!state.selectedBulkProducts || state.selectedBulkProducts.length === 0) {
        showToast('Không có sản phẩm nào trong danh sách để tạo.', false);
        return;
    }

    // Flush form hiện tại
    flushActiveProductFormToState();

    const count = state.selectedBulkProducts.length;
    const storeName = state.currentStoreType === 'custom' ? 'Store Riêng (qua US Proxy Gate)' : 'Store Mặc định';

    // Chốt chặn xác nhận trước khi tạo hàng loạt (Confirmation Gate)
    if (typeof Swal !== 'undefined') {
        const confirmResult = await Swal.fire({
            title: 'Xác nhận tạo hàng loạt',
            html: `
                <div class="text-left text-sm text-gray-700 space-y-3">
                    <p>Bạn có chắc chắn muốn tiến hành tạo <b>${count} sản phẩm</b> đã chọn lên <b>${escapeHtml(storeName)}</b>?</p>
                    <div class="p-3.5 bg-amber-50 rounded-xl border border-amber-200 space-y-2 text-sm text-amber-900">
                        <div class="flex items-center gap-2 font-bold text-amber-950 text-sm">
                            <iconify-icon icon="mdi:alert-circle-outline" class="text-lg"></iconify-icon>
                            <span>Lưu ý quan trọng:</span>
                        </div>
                        <p class="text-sm text-amber-900 leading-relaxed font-medium">
                            Hệ thống sẽ xếp hàng ${count} sản phẩm và tiến hành tạo tự động qua Shopify GraphQL API. Bạn có thể theo dõi tiến trình trực tiếp theo thời gian thực.
                        </p>
                    </div>
                </div>
            `,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: `Tiến hành tạo ${count} sản phẩm`,
            cancelButtonText: 'Hủy bỏ',
            confirmButtonColor: '#4f46e5',
            cancelButtonColor: '#6b7280',
            reverseButtons: true,
            focusCancel: false,
            customClass: {
                popup: '!rounded-2xl !p-6'
            }
        });
        if (!confirmResult.isConfirmed) {
            return;
        }
    }

    closeBulkOverviewModal();

    const progressModal = document.getElementById('bulkProgressModal');
    const progressBar = document.getElementById('bulk-progress-bar-fill') || document.getElementById('bulk-progress-bar');
    const progressPercent = document.getElementById('bulk-progress-percent');
    const summaryBadge = document.getElementById('bulk-progress-stats') || document.getElementById('bulk-summary-badge');
    const tbody = document.getElementById('bulk-progress-table-body');
    const closeBtn = document.getElementById('btn-close-progress-modal') || document.getElementById('btn-progress-done') || document.getElementById('btn-close-bulk-progress');
    const doneBtn = document.getElementById('btn-progress-done');

    if (!progressModal || !tbody) return;

    // Khóa nút đóng khi đang thực thi
    if (closeBtn) closeBtn.disabled = true;
    if (doneBtn) doneBtn.classList.add('hidden');

    // Reset giao diện Progress
    if (progressBar) progressBar.style.width = '0%';
    if (progressPercent) progressPercent.textContent = `0/${state.selectedBulkProducts.length} (0%)`;
    if (summaryBadge) {
        summaryBadge.textContent = 'Đang khởi tạo Bulk Job...';
        summaryBadge.className = 'text-sm font-semibold px-3 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded-full';
    }

    // Render bảng tiến trình rỗng
    tbody.innerHTML = state.selectedBulkProducts.map((item, idx) => `
        <tr id="bulk-progress-row-${idx}" class="hover:bg-gray-50/80 transition-colors">
            <td class="px-3.5 py-3 text-sm font-semibold text-gray-700 text-center">${idx + 1}</td>
            <td class="px-3.5 py-3 text-sm font-mono text-gray-600 font-semibold truncate max-w-[160px]">${escapeHtml(item.handle || '—')}</td>
            <td class="px-3.5 py-3 text-sm font-bold text-gray-900 truncate max-w-[220px]">${escapeHtml(item.title || '—')}</td>
            <td class="px-3.5 py-3 text-sm text-center" id="bulk-progress-status-${idx}">
                <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-gray-100 text-gray-600">
                    <iconify-icon icon="mdi:clock-outline" class="text-sm"></iconify-icon>
                    <span>Chờ tạo</span>
                </span>
            </td>
            <td class="px-3.5 py-3 text-sm" id="bulk-progress-result-${idx}">
                <span class="text-sm text-gray-400">—</span>
            </td>
        </tr>
    `).join('');

    progressModal.classList.remove('hidden');

    try {
        // Step 1: Chuẩn bị Bulk Job
        const payloadList = state.selectedBulkProducts.map(item => item.payload);
        const prepResp = await fetch('/api/products/bulk-jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                store_type: state.currentStoreType,
                items: payloadList,
                products: payloadList
            })
        });

        const prepResult = await prepResp.json();
        if (!prepResp.ok || !prepResult.success) {
            throw new Error(prepResult.error || 'Không thể chuẩn bị Bulk Job');
        }

        const jobId = prepResult.job_id || (prepResult.job && prepResult.job.job_id);

        // Step 2: Bắt đầu chạy Worker
        const startResp = await fetch(`/api/products/bulk-jobs/${jobId}/start`, {
            method: 'POST'
        });
        const startResult = await startResp.json();
        if (!startResp.ok || !startResult.success) {
            throw new Error(startResult.error || 'Không thể kích hoạt Bulk Job Worker');
        }

        // Step 3: Kết nối Server-Sent Events theo dõi tiến trình
        connectBulkJobEventSource(jobId, state.selectedBulkProducts.length);

    } catch (err) {
        if (summaryBadge) {
            summaryBadge.textContent = 'Lỗi khởi tạo: ' + err.message;
            summaryBadge.className = 'text-sm font-semibold px-3 py-1 bg-red-50 text-red-700 border border-red-200 rounded-full';
        }
        if (closeBtn) closeBtn.disabled = false;
        Swal.fire({
            icon: 'error',
            title: 'Khởi tạo thất bại',
            text: err.message
        });
    }
}

/**
 * Kết nối Server-Sent Events (SSE) theo dõi tiến trình tạo sản phẩm hàng loạt
 */
function connectBulkJobEventSource(jobId, totalItems) {
    const progressBar = document.getElementById('bulk-progress-bar-fill') || document.getElementById('bulk-progress-bar');
    const progressPercent = document.getElementById('bulk-progress-percent');
    const summaryBadge = document.getElementById('bulk-progress-stats') || document.getElementById('bulk-summary-badge');
    const closeBtn = document.getElementById('btn-close-progress-modal') || document.getElementById('btn-progress-done') || document.getElementById('btn-close-bulk-progress');
    const doneBtn = document.getElementById('btn-progress-done');

    let completedCount = 0;
    let failedCount = 0;

    const evtSource = new EventSource(`/api/products/bulk-jobs/${jobId}/events`);

    const updateProgress = () => {
        const finished = completedCount + failedCount;
        const pct = Math.min(100, Math.round((finished / totalItems) * 100));
        if (progressBar) progressBar.style.width = `${pct}%`;
        if (progressPercent) progressPercent.textContent = `${finished}/${totalItems} (${pct}%)`;
        if (summaryBadge) {
            summaryBadge.textContent = `Đang xử lý: ${completedCount} thành công, ${failedCount} lỗi`;
            summaryBadge.className = 'text-sm font-semibold px-3 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full';
        }
    };

    // Named SSE listeners
    evtSource.addEventListener('job_started', () => {
        if (summaryBadge) {
            summaryBadge.textContent = 'Tiến trình đang chạy...';
        }
    });

    evtSource.addEventListener('item_started', (e) => {
        try {
            const data = JSON.parse(e.data);
            const idx = data.item_index;
            const statusEl = document.getElementById(`bulk-progress-status-${idx}`);
            if (statusEl) {
                statusEl.innerHTML = `
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-blue-100 text-blue-800 animate-pulse">
                        <svg class="animate-spin h-3.5 w-3.5 text-blue-600" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span>Đang tạo...</span>
                    </span>
                `;
            }
        } catch (err) {
            console.warn('Error parsing item_started event', err);
        }
    });

    evtSource.addEventListener('item_throttled', (e) => {
        try {
            const data = JSON.parse(e.data);
            const idx = data.item_index;
            const statusEl = document.getElementById(`bulk-progress-status-${idx}`);
            if (statusEl) {
                statusEl.innerHTML = `
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-amber-100 text-amber-800">
                        <iconify-icon icon="mdi:speedometer-slow" class="text-sm"></iconify-icon>
                        <span>Throttled (${data.wait_seconds}s)...</span>
                    </span>
                `;
            }
        } catch (err) {
            console.warn('Error parsing item_throttled event', err);
        }
    });

    evtSource.addEventListener('item_succeeded', (e) => {
        try {
            const data = JSON.parse(e.data);
            const idx = data.item_index;
            completedCount++;
            updateProgress();

            const statusEl = document.getElementById(`bulk-progress-status-${idx}`);
            const resultEl = document.getElementById(`bulk-progress-result-${idx}`);

            if (statusEl) {
                statusEl.innerHTML = `
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-emerald-100 text-emerald-800">
                        <iconify-icon icon="mdi:check-circle" class="text-sm text-emerald-600"></iconify-icon>
                        <span>Thành công</span>
                    </span>
                `;
            }

            if (resultEl) {
                const links = data.links || {};
                resultEl.innerHTML = `
                    <div class="flex items-center gap-2 flex-wrap">
                        ${links.shopify_admin ? `<a href="${links.shopify_admin}" target="_blank" class="inline-flex items-center gap-1 px-2.5 py-1 text-sm font-semibold bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"><iconify-icon icon="mdi:shopify"></iconify-icon>Admin</a>` : ''}
                        ${links.storefront ? `<a href="${links.storefront}" target="_blank" class="inline-flex items-center gap-1 px-2.5 py-1 text-sm font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg transition-colors"><iconify-icon icon="mdi:web"></iconify-icon>Storefront</a>` : ''}
                        ${links.tool ? `<a href="${links.tool}" target="_blank" class="inline-flex items-center gap-1 px-2.5 py-1 text-sm font-semibold bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg transition-colors"><iconify-icon icon="mdi:open-in-new"></iconify-icon>Tool</a>` : ''}
                    </div>
                `;
            }

            if (state.selectedBulkProducts[idx]) {
                state.selectedBulkProducts[idx].status = 'SUCCESS';
                state.selectedBulkProducts[idx].links = data.links;
            }
        } catch (err) {
            console.warn('Error parsing item_succeeded event', err);
        }
    });

    evtSource.addEventListener('item_failed', (e) => {
        try {
            const data = JSON.parse(e.data);
            const idx = data.item_index;
            failedCount++;
            updateProgress();

            const statusEl = document.getElementById(`bulk-progress-status-${idx}`);
            const resultEl = document.getElementById(`bulk-progress-result-${idx}`);

            if (statusEl) {
                statusEl.innerHTML = `
                    <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-red-100 text-red-800" title="${escapeHtml(data.error || '')}">
                        <iconify-icon icon="mdi:alert-circle" class="text-sm text-red-600"></iconify-icon>
                        <span>Lỗi</span>
                    </span>
                `;
            }

            if (resultEl) {
                resultEl.innerHTML = `<span class="text-sm text-red-600 font-medium truncate block max-w-[240px]" title="${escapeHtml(data.error || '')}">${escapeHtml(data.error || 'Tạo thất bại')}</span>`;
            }

            if (state.selectedBulkProducts[idx]) {
                state.selectedBulkProducts[idx].status = 'ERROR';
                state.selectedBulkProducts[idx].error = data.error;
            }
        } catch (err) {
            console.warn('Error parsing item_failed event', err);
        }
    });

    evtSource.addEventListener('job_paused', (e) => {
        try {
            const data = JSON.parse(e.data);
            if (summaryBadge) {
                summaryBadge.textContent = 'Tạm dừng: Gặp sự cố kết nối US Proxy an toàn';
                summaryBadge.className = 'text-sm font-semibold px-3 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full';
            }
            if (closeBtn) closeBtn.disabled = false;
            evtSource.close();
            Swal.fire({
                icon: 'warning',
                title: 'Tiến trình tạm dừng',
                text: `Tiến trình đã tự động dừng an toàn để tránh làm hỏng các sản phẩm tiếp theo do lỗi US Proxy: ${data.proxy_error || data.reason || 'Lỗi mạng proxy'}`
            });
        } catch (err) {
            console.warn('Error parsing job_paused event', err);
        }
    });

    evtSource.addEventListener('job_completed', (e) => {
        try {
            const data = JSON.parse(e.data);
            evtSource.close();
            if (progressBar) progressBar.style.width = '100%';
            if (progressPercent) progressPercent.textContent = `${totalItems}/${totalItems} (100%)`;
            if (closeBtn) closeBtn.disabled = false;
            if (doneBtn) doneBtn.classList.remove('hidden');

            const successTotal = data.completed_items ?? completedCount;
            const failedTotal = data.failed_items ?? failedCount;

            if (summaryBadge) {
                summaryBadge.textContent = `Hoàn thành: ${successTotal} thành công, ${failedTotal} lỗi`;
                summaryBadge.className = `text-sm font-semibold px-3 py-1 rounded-full ${failedTotal === 0 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`;
            }

            Swal.fire({
                icon: failedTotal === 0 ? 'success' : 'warning',
                title: 'Hoàn tất tạo sản phẩm hàng loạt',
                html: `
                    <div class="text-left text-sm text-gray-700 space-y-2">
                        <p>Đã xử lý xong toàn bộ <b>${totalItems}</b> sản phẩm.</p>
                        <p class="text-emerald-700 font-semibold">&bull; Thành công: <b>${successTotal}</b> sản phẩm</p>
                        ${failedTotal > 0 ? `<p class="text-red-600 font-semibold">&bull; Lỗi: <b>${failedTotal}</b> sản phẩm</p>` : ''}
                        <p class="text-gray-500 mt-2">Bạn có thể bấm vào các link Admin / Storefront / Tool trong bảng để kiểm tra sản phẩm vừa tạo.</p>
                    </div>
                `,
                confirmButtonText: 'Đã hiểu'
            });
        } catch (err) {
            console.warn('Error parsing job_completed event', err);
        }
    });

    evtSource.onerror = (err) => {
        console.warn('SSE EventSource error/closed:', err);
        if (closeBtn) closeBtn.disabled = false;
    };
}

/**
 * Đóng modal tiến trình tạo hàng loạt
 */
function closeBulkProgressModal() {
    const modal = document.getElementById('bulkProgressModal');
    if (modal) modal.classList.add('hidden');
}
