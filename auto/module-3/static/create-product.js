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
    // Cờ bật/tắt hiển thị các tổ hợp biến thể đã bỏ qua (Sparse Variants)
    showDisabledVariants: false,
    // Bộ nhớ đệm Taxonomy ID theo đường dẫn danh mục CSV
    taxonomyCacheByPath: {},

    isSubmitting: false,

    // Quản lý sản phẩm hàng loạt (Bulk Product Creation)
    selectedBulkProducts: [], // [{ clientId, handle, title, descriptionHtml, payload, status: 'PENDING'|'RUNNING'|'SUCCESS'|'ERROR', error: null, links: null }]
    activeBulkProductId: null,
    selectedCsvHandles: new Set(),
    currentBulkJobSnapshot: null,
    bulkInlineFilter: 'all',
    isBulkJobRunning: false,
    bulkFallbackPollTimer: null,

    // Bản lưu trữ tạo gần nhất (JSON lưu trên server)
    latestArchiveData: null,
    latestArchiveFilter: 'all',
    latestArchiveSearchQuery: '',
    pendingAuthorName: ''
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

    // Kiểm tra nếu có Bulk Job đang chạy nền thì tiếp tục lắng nghe SSE
    checkRunningBulkJobOnLoad();

    // Tải thông tin Bản lưu trữ tạo gần nhất trên server để cập nhật badge số lượng
    refreshLatestArchiveSummary();

    // Gắn sự kiện click trực tiếp cho nút xem chi tiết thiếu ở thanh dưới cùng
    const missingBtn = document.getElementById('btn-show-missing-fields');
    if (missingBtn) {
        missingBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            showMissingFieldsModal();
        });
    }
    const hintText = document.getElementById('submit-hint-text');
    if (hintText) {
        hintText.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            showMissingFieldsModal();
        });
    }

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
 * Tính toán toàn bộ tổ hợp biến thể (Cartesian) và phân loại:
 * - activeCombinations: Các biến thể đang bật (enabled !== false) sẽ được tạo thực tế
 * - disabledCombinations: Các tổ hợp không bán / đã bỏ qua (enabled === false)
 */
function getActiveVariantCombinations() {
    const validOptions = state.options.filter(o => o.name.trim() && o.values.length > 0);
    if (validOptions.length === 0) {
        return {
            validOptions: [],
            allCombinations: [],
            activeCombinations: [],
            disabledCombinations: []
        };
    }

    const optionArrays = validOptions.map(o => o.values.map(v => ({
        optionName: o.name,
        valueId: v.clientId,
        valueLabel: v.label
    })));

    const allCombinations = optionArrays.reduce((acc, curr) => {
        const res = [];
        acc.forEach(a => {
            curr.forEach(c => {
                res.push([...a, c]);
            });
        });
        return res;
    }, [[]]);

    const activeCombinations = [];
    const disabledCombinations = [];

    allCombinations.forEach(comb => {
        const combKey = comb.map(c => c.valueId).join('_');
        if (!state.variantsByKey[combKey]) {
            state.variantsByKey[combKey] = {
                enabled: true,
                price: '',
                compareAtPrice: '',
                sku: '',
                barcode: ''
            };
        } else if (state.variantsByKey[combKey].enabled === undefined) {
            state.variantsByKey[combKey].enabled = true;
        }

        if (state.variantsByKey[combKey].enabled === false) {
            disabledCombinations.push(comb);
        } else {
            activeCombinations.push(comb);
        }
    });

    return {
        validOptions,
        allCombinations,
        activeCombinations,
        disabledCombinations
    };
}

/**
 * Xây dựng optionsPayload (đã lọc bỏ giá trị không dùng) và variantsPayload (chỉ lấy biến thể đang bật)
 * từ trạng thái form hiện tại — đảm bảo Single Source of Truth cho cả Single & Bulk Creation.
 */
function buildPrunedOptionsAndVariantsFromState() {
    const { validOptions, activeCombinations } = getActiveVariantCombinations();
    const usedValueIds = new Set();

    const variantsPayload = activeCombinations.map(comb => {
        const combKey = comb.map(c => c.valueId).join('_');
        const row = state.variantsByKey[combKey] || {};
        comb.forEach(c => usedValueIds.add(c.valueId));
        return {
            optionValues: comb.map(c => ({
                optionName: c.optionName.trim(),
                name: c.valueLabel
            })),
            price: String(row.price !== undefined && row.price !== null ? row.price : '').trim(),
            compareAtPrice: String(row.compareAtPrice !== undefined && row.compareAtPrice !== null ? row.compareAtPrice : '').trim(),
            sku: String(row.sku || '').trim(),
            barcode: String(row.barcode || '').trim()
        };
    });

    const optionsPayload = validOptions.map(o => ({
        name: o.name.trim(),
        values: o.values
            .filter(v => usedValueIds.has(v.clientId))
            .map(v => ({ label: v.label }))
    })).filter(o => o.values.length > 0);

    return { optionsPayload, variantsPayload };
}

/**
 * Cập nhật trạng thái hiển thị của nút "Bỏ qua tổ hợp trống" và "Hiện/Ẩn tổ hợp đã ẩn"
 */
function syncVariantToolbarControls(activeCombinations, disabledCombinations) {
    const toggleBtn = document.getElementById('btn-toggle-disabled-variants');
    const toggleIcon = document.getElementById('toggle-disabled-variants-icon');
    const toggleText = document.getElementById('toggle-disabled-variants-text');

    if (toggleBtn && toggleText) {
        if (disabledCombinations.length > 0) {
            toggleBtn.classList.remove('hidden');
            toggleBtn.classList.add('inline-flex');
            if (state.showDisabledVariants) {
                toggleText.textContent = `Ẩn ${disabledCombinations.length} tổ hợp không dùng`;
                if (toggleIcon) toggleIcon.setAttribute('icon', 'mdi:eye-off-outline');
            } else {
                toggleText.textContent = `Hiện ${disabledCombinations.length} tổ hợp đã ẩn`;
                if (toggleIcon) toggleIcon.setAttribute('icon', 'mdi:eye-outline');
            }
        } else {
            state.showDisabledVariants = false;
            toggleBtn.classList.add('hidden');
            toggleBtn.classList.remove('inline-flex');
        }
    }

    const disableEmptyBtn = document.getElementById('btn-disable-empty-variants');
    const disableEmptyText = document.getElementById('disable-empty-variants-text');
    if (disableEmptyBtn && disableEmptyText) {
        let emptyActiveCount = 0;
        activeCombinations.forEach(comb => {
            const combKey = comb.map(c => c.valueId).join('_');
            const row = state.variantsByKey[combKey] || {};
            if (row.price === '' || row.price === undefined || row.price === null) {
                emptyActiveCount++;
            }
        });
        const filledCount = activeCombinations.length - emptyActiveCount;
        if (emptyActiveCount > 0 && filledCount >= 1) {
            disableEmptyBtn.classList.remove('hidden');
            disableEmptyBtn.classList.add('inline-flex');
            disableEmptyText.textContent = `Bỏ qua ${emptyActiveCount} tổ hợp trống`;
        } else {
            disableEmptyBtn.classList.add('hidden');
            disableEmptyBtn.classList.remove('inline-flex');
        }
    }
}

/**
 * Tái tạo ma trận biến thể (hỗ trợ Sparse / Non-exhaustive Variants).
 * Sử dụng combination key ổn định dựa trên value clientId để không làm mất giá & SKU.
 */
function rebuildVariantMatrix() {
    const tbody = document.getElementById('variant-matrix-tbody');
    const summary = document.getElementById('variant-matrix-summary');
    if (!tbody) return;

    const {
        validOptions,
        allCombinations,
        activeCombinations,
        disabledCombinations
    } = getActiveVariantCombinations();

    if (validOptions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-4 py-8 text-center text-gray-400 text-sm">
                    Vui lòng nhập tên tùy chọn và ít nhất 1 giá trị để tạo ma trận biến thể.
                </td>
            </tr>
        `;
        if (summary) summary.textContent = '0 tùy chọn • 0 biến thể';
        syncVariantToolbarControls([], []);
        return;
    }

    if (summary) {
        if (disabledCombinations.length > 0) {
            summary.textContent = `${validOptions.length} tùy chọn • ${activeCombinations.length} biến thể đang bật (bỏ qua ${disabledCombinations.length} tổ hợp)`;
        } else {
            summary.textContent = `${validOptions.length} tùy chọn • ${activeCombinations.length} biến thể`;
        }
    }

    syncVariantToolbarControls(activeCombinations, disabledCombinations);

    const rowsToRender = state.showDisabledVariants ? allCombinations : activeCombinations;
    const canDisableMore = activeCombinations.length > 1;

    // Tối ưu render ma trận biến thể bằng DocumentFragment (tránh reflow lặp lại)
    const fragment = document.createDocumentFragment();
    const tempTbody = document.createElement('tbody');

    if (rowsToRender.length === 0) {
        tempTbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-4 py-8 text-center text-gray-500 text-sm">
                    Tất cả tổ hợp biến thể hiện đang bị ẩn. Hãy bấm <b>"Hiện tổ hợp đã ẩn"</b> phía trên để bật lại ít nhất 1 biến thể.
                </td>
            </tr>
        `;
    } else {
        tempTbody.innerHTML = rowsToRender.map((comb) => {
            const combKey = comb.map(c => c.valueId).join('_');
            const title = comb.map(c => c.valueLabel).join(' / ');
            const rowData = state.variantsByKey[combKey];
            const isEnabled = rowData.enabled !== false;

            if (!isEnabled) {
                return `
                    <tr class="bg-gray-50/80 text-gray-400 transition-colors" data-comb-key="${combKey}" data-variant-enabled="false">
                        <td class="px-4 py-2.5 font-semibold">
                            <span class="inline-block px-2.5 py-1 bg-gray-100 rounded-md text-sm text-gray-400 line-through border border-gray-200">
                                ${escapeHtml(title)}
                            </span>
                        </td>
                        <td colspan="4" class="px-3 py-2.5 text-sm text-gray-500 italic">
                            Tổ hợp này không bán — sẽ không tạo biến thể trên Shopify Store.
                        </td>
                        <td class="px-3 py-2.5 text-center">
                            <button type="button" onclick="toggleVariantRowEnabled('${combKey}', true)" class="inline-flex items-center gap-1 px-2.5 py-1 bg-indigo-50 hover:bg-indigo-600 text-indigo-700 hover:text-white text-sm font-semibold rounded-lg border border-indigo-200 transition-colors cursor-pointer" title="Khôi phục tổ hợp này thành biến thể đang bán">
                                <iconify-icon icon="mdi:plus-circle-outline" class="text-base"></iconify-icon>
                                <span>Bật bán</span>
                            </button>
                        </td>
                    </tr>
                `;
            }

            const pVal = parseFloat(rowData.price);
            const cVal = parseFloat(rowData.compareAtPrice);
            const isCompareInvalid = (!isNaN(pVal) && !isNaN(cVal) && cVal <= pVal);

            return `
                <tr class="hover:bg-gray-50/70 transition-colors ${isCompareInvalid ? 'bg-red-50/40' : ''}" data-comb-key="${combKey}" data-variant-enabled="true">
                    <td class="px-4 py-3 font-semibold text-gray-900">
                        <span class="inline-block px-2.5 py-1 bg-gray-100 rounded-md text-sm text-gray-800 border border-gray-200">
                            ${escapeHtml(title)}
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
                        <input type="text" value="${escapeHtml(rowData.sku || '')}" oninput="handleVariantFieldChange('${combKey}', 'sku', this.value)" placeholder="Mã SKU..." class="w-full px-2.5 py-1.5 bg-gray-50 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white font-mono">
                    </td>
                    <td class="px-3 py-3">
                        <input type="text" value="${escapeHtml(rowData.barcode || '')}" oninput="handleVariantFieldChange('${combKey}', 'barcode', this.value)" placeholder="Mã Barcode..." class="w-full px-2.5 py-1.5 bg-gray-50 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white font-mono">
                    </td>
                    <td class="px-3 py-3 text-center">
                        <button type="button" onclick="toggleVariantRowEnabled('${combKey}', false)" ${canDisableMore ? '' : 'disabled'} class="inline-flex items-center gap-1 px-2.5 py-1.5 text-sm font-semibold rounded-lg border transition-colors ${canDisableMore ? 'bg-gray-50 hover:bg-red-50 text-gray-600 hover:text-red-700 border-gray-200 hover:border-red-200 cursor-pointer' : 'bg-gray-50 text-gray-300 border-gray-100 cursor-not-allowed'}" title="${canDisableMore ? 'Bỏ qua tổ hợp này (không tạo biến thể)' : 'Sản phẩm cần tối thiểu 1 biến thể đang bật'}">
                            <iconify-icon icon="mdi:eye-off-outline" class="text-base"></iconify-icon>
                            <span>Bỏ qua</span>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

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

function toggleVariantRowEnabled(combKey, shouldEnable) {
    const { activeCombinations } = getActiveVariantCombinations();
    if (!shouldEnable && activeCombinations.length <= 1) {
        showToast('Sản phẩm bắt buộc phải có ít nhất 1 biến thể đang bật.', false);
        return;
    }
    if (!state.variantsByKey[combKey]) {
        state.variantsByKey[combKey] = {
            enabled: !!shouldEnable,
            price: '',
            compareAtPrice: '',
            sku: '',
            barcode: ''
        };
    } else {
        state.variantsByKey[combKey].enabled = !!shouldEnable;
    }
    rebuildVariantMatrix();
    updateValidationState();
}

function toggleShowDisabledVariants() {
    state.showDisabledVariants = !state.showDisabledVariants;
    rebuildVariantMatrix();
}

function disableEmptyVariants() {
    const { activeCombinations } = getActiveVariantCombinations();
    const emptyKeys = [];
    activeCombinations.forEach(comb => {
        const combKey = comb.map(c => c.valueId).join('_');
        const row = state.variantsByKey[combKey] || {};
        if (row.price === '' || row.price === undefined || row.price === null) {
            emptyKeys.push(combKey);
        }
    });

    if (emptyKeys.length === 0) return;
    if (emptyKeys.length >= activeCombinations.length) {
        showToast('Vui lòng điền giá cho ít nhất 1 biến thể trước khi ẩn các dòng trống.', false);
        return;
    }

    emptyKeys.forEach(k => {
        if (state.variantsByKey[k]) {
            state.variantsByKey[k].enabled = false;
        }
    });
    state.showDisabledVariants = false;
    rebuildVariantMatrix();
    updateValidationState();
    showToast(`Đã bỏ qua ${emptyKeys.length} tổ hợp biến thể trống.`, true);
}

window.toggleVariantRowEnabled = toggleVariantRowEnabled;
window.toggleShowDisabledVariants = toggleShowDisabledVariants;
window.disableEmptyVariants = disableEmptyVariants;

function handleVariantFieldChange(combKey, field, val) {
    if (!state.variantsByKey[combKey]) {
        state.variantsByKey[combKey] = { enabled: true };
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
        const { activeCombinations, disabledCombinations } = getActiveVariantCombinations();
        syncVariantToolbarControls(activeCombinations, disabledCombinations);
    }
    updateValidationState();
}

function promptBulkPricing() {
    const { activeCombinations } = getActiveVariantCombinations();
    if (activeCombinations.length === 0) {
        showToast('Không có biến thể nào đang bật để điền giá.', false);
        return;
    }

    const price = prompt("Nhập Giá Bán ($) cho toàn bộ các biến thể đang bật:", "129.00");
    if (price === null) return;
    const compareAt = prompt("Nhập Giá So Sánh ($) cho toàn bộ các biến thể đang bật:", "159.00");
    if (compareAt === null) return;

    const baseSkuPrefix = prompt("Nhập tiền tố SKU (ví dụ: WRY-SHELF):", "WRY-PROD");

    let counter = 1;
    const timestamp = Date.now().toString().slice(-6);

    activeCombinations.forEach(comb => {
        const key = comb.map(c => c.valueId).join('_');
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

        // Nếu form đang có sẵn tác giả từ Bản lưu trữ / CSV thì kiểm tra khớp trên store hiện tại
        let resolvedAuthor = null;
        const candidateId = (hiddenInput && hiddenInput.value) ? hiddenInput.value : state.selectedAuthorId;
        if (candidateId) {
            resolvedAuthor = state.authors.find(a => a.id === candidateId) || null;
        }
        if (!resolvedAuthor && state.pendingAuthorName) {
            const targetName = state.pendingAuthorName.trim().toLowerCase();
            resolvedAuthor = state.authors.find(a =>
                String(a.name || a.displayName || '').trim().toLowerCase() === targetName ||
                String(a.handle || '').trim().toLowerCase() === targetName
            ) || null;
        }
        if (!resolvedAuthor && state.authors.length > 0) {
            resolvedAuthor = state.authors[0];
        }
        if (resolvedAuthor) {
            state.selectedAuthorId = resolvedAuthor.id;
            state.selectedAuthorData = resolvedAuthor;
            if (hiddenInput) hiddenInput.value = resolvedAuthor.id;
        }

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

    // Variants validity (chỉ kiểm tra trên các biến thể đang bật — hỗ trợ Sparse Variants)
    const { validOptions, activeCombinations } = getActiveVariantCombinations();
    let variantsValid = false;
    let variantsReason = '';

    if (validOptions.length === 0) {
        variantsReason = 'Chưa thiết lập tùy chọn và giá trị biến thể';
    } else if (validOptions.length > 3) {
        variantsReason = 'Số lượng tùy chọn không được vượt quá 3';
    } else if (activeCombinations.length === 0) {
        variantsReason = 'Cần bật ít nhất 1 biến thể để bán trên Store';
    } else if (activeCombinations.length > 2048) {
        variantsReason = 'Số lượng biến thể đang bật vượt quá giới hạn 2048';
    } else {
        let allComplete = true;
        const seenSkus = new Set();
        const seenBarcodes = new Set();

        for (const comb of activeCombinations) {
            const k = comb.map(c => c.valueId).join('_');
            const combLabel = comb.map(c => c.valueLabel).join(' / ');
            const row = state.variantsByKey[k];
            if (!row) {
                allComplete = false;
                variantsReason = `Biến thể "${combLabel}" chưa được thiết lập dữ liệu`;
                break;
            }
            const rawPrice = String(row.price !== undefined && row.price !== null ? row.price : '').trim();
            const priceNum = parseFloat(rawPrice);
            if (!rawPrice || isNaN(priceNum) || priceNum < 0) {
                allComplete = false;
                variantsReason = `Biến thể "${combLabel}": Giá bán biến thể chưa hợp lệ (phải >= 0)`;
                break;
            }
            const rawCompare = String(row.compareAtPrice !== undefined && row.compareAtPrice !== null ? row.compareAtPrice : '').trim();
            const compareNum = parseFloat(rawCompare);
            if (!rawCompare || isNaN(compareNum) || compareNum <= priceNum) {
                allComplete = false;
                variantsReason = `Biến thể "${combLabel}": Giá so sánh phải lớn hơn Giá bán`;
                break;
            }
            const skuVal = String(row.sku || '').trim();
            if (!skuVal) {
                allComplete = false;
                variantsReason = `Biến thể "${combLabel}": Thiếu mã SKU`;
                break;
            }
            if (seenSkus.has(skuVal.toLowerCase())) {
                allComplete = false;
                variantsReason = `Biến thể "${combLabel}": Mã SKU "${skuVal}" bị trùng lặp`;
                break;
            }
            seenSkus.add(skuVal.toLowerCase());

            const barcodeVal = String(row.barcode || '').trim();
            if (!barcodeVal) {
                allComplete = false;
                variantsReason = `Biến thể "${combLabel}": Thiếu Barcode`;
                break;
            }
            if (seenBarcodes.has(barcodeVal.toLowerCase())) {
                allComplete = false;
                variantsReason = `Biến thể "${combLabel}": Barcode "${barcodeVal}" bị trùng lặp`;
                break;
            }
            seenBarcodes.add(barcodeVal.toLowerCase());
        }
        variantsValid = allComplete;
    }

    const missing = [];
    const completed = [];

    const fieldChecks = [
        { key: 'media', valid: state.media && state.media.length > 0, label: '1. Phương tiện (Media)', hint: 'Thêm ít nhất 1 ảnh từ máy tính hoặc URL', targetId: 'image-url-input' },
        { key: 'title', valid: !!title, label: '2. Tên sản phẩm (Title)', hint: 'Nhập tên sản phẩm', targetId: 'product-title' },
        { key: 'desc', valid: !!desc, label: '3. Mô tả ngắn (Description)', hint: 'Nhập mô tả tóm tắt cho sản phẩm', targetId: 'product-desc' },
        { key: 'productType', valid: !!productType, label: '4. Loại sản phẩm (Type)', hint: 'Nhập loại sản phẩm (ví dụ: wood-floor-lamp-base...)', targetId: 'product-type' },
        { key: 'category', valid: !!categoryId, label: '5. Danh mục (Category)', hint: 'Bấm nút "Chọn" để chọn danh mục chuẩn Shopify', targetId: 'selected-category-name' },
        { key: 'status', valid: !!status, label: '6. Trạng thái (Status)', hint: 'Chọn trạng thái Draft hoặc Active', targetId: 'product-status' },
        { key: 'vendor', valid: !!vendor, label: '7. Nhà cung cấp (Vendor)', hint: 'Chọn hoặc nhập nhà cung cấp (mặc định: Wrydeco)', targetId: 'product-vendor' },
        { key: 'tags', valid: state.tags && state.tags.length > 0, label: '8. Thẻ sản phẩm (Tags)', hint: 'Nhập ít nhất 1 tag và nhấn Enter', targetId: 'tag-input' },
        { key: 'seoTitle', valid: !!seoTitle, label: '9. Tiêu đề SEO (SEO Title)', hint: 'Nhập tiêu đề trang hiển thị trên Google', targetId: 'seo-title' },
        { key: 'seoDesc', valid: !!seoDesc, label: '10. Mô tả SEO (SEO Description)', hint: 'Nhập mô tả meta hiển thị trên Google', targetId: 'seo-desc' },
        { key: 'author', valid: !!authorId, label: '11. Tác giả thiết kế (Author)', hint: 'Chọn 1 nghệ nhân chế tác từ danh sách', targetId: 'inline-authors-container' },
        { key: 'richDesc', valid: !!richDesc, label: '12. Mô tả mở rộng (Rich Description)', hint: 'Nhập nội dung mô tả chi tiết sản phẩm', targetId: 'rich-description' },
        { key: 'aeoHtml', valid: !!aeoHtml, label: '13. Nội dung tìm kiếm AI (AEO)', hint: 'Nhập câu hỏi/đáp và tóm tắt cho AI tìm kiếm', targetId: 'aeo-html' },
        { key: 'interiorStyle', valid: checkedInterior.length > 0, label: '14. Phong cách nội thất (Interior Style)', hint: 'Chọn ít nhất 1 phong cách phù hợp', targetId: 'interior-style-container' },
        { key: 'roomType', valid: checkedRoom.length > 0, label: '15. Không gian phòng (Room Type)', hint: 'Chọn ít nhất 1 không gian phòng', targetId: 'room-type-container' },
        { key: 'variants', valid: variantsValid, label: '16. Biến thể sản phẩm (Variants)', hint: variantsReason || 'Điền đầy đủ Giá bán, Giá so sánh (> Giá bán), SKU và Barcode', targetId: 'variant-matrix-tbody' }
    ];

    fieldChecks.forEach(f => {
        if (f.valid) {
            completed.push(f);
        } else {
            missing.push(f);
        }
    });

    const completedCount = completed.length;
    const isAllValid = (missing.length === 0);

    return {
        isAllValid,
        completedCount,
        missing,
        completed
    };
}

/**
 * Render nội dung cho Popup tự viết #missingFieldsModal (không sử dụng SweetAlert2)
 */
function renderMissingFieldsModalContent(valInfo) {
    const countCompleted = valInfo.completedCount;
    const countMissing = valInfo.missing.length;
    const pct = Math.min(100, Math.round((countCompleted / 16) * 100));

    const iconBox = document.getElementById('missing-fields-header-icon-box');
    const iconEl = document.getElementById('missing-fields-header-icon');
    const subtitleEl = document.getElementById('missing-fields-header-subtitle');
    const progressBadge = document.getElementById('missing-fields-progress-badge');
    const progressBar = document.getElementById('missing-fields-progress-bar');
    const bodyEl = document.getElementById('missing-fields-modal-body');
    const jumpFirstBtn = document.getElementById('btn-missing-jump-first');

    if (iconBox && iconEl) {
        if (valInfo.isAllValid) {
            iconBox.className = 'w-11 h-11 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center shrink-0';
            iconEl.setAttribute('icon', 'mdi:check-decagram');
        } else {
            iconBox.className = 'w-11 h-11 rounded-xl bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center shrink-0';
            iconEl.setAttribute('icon', 'mdi:clipboard-alert-outline');
        }
    }

    if (subtitleEl) {
        subtitleEl.textContent = valInfo.isAllValid
            ? 'Tất cả 16 trường bắt buộc đã hợp lệ. Biểu mẫu sẵn sàng tạo sản phẩm!'
            : `Còn ${countMissing} trường bắt buộc chưa hoàn thiện. Bấm "Điền ngay" để chuyển tới đúng trường.`;
    }

    if (progressBadge) {
        progressBadge.textContent = `${countCompleted}/16 trường hợp lệ`;
        progressBadge.className = valInfo.isAllValid
            ? 'px-3 py-1 rounded-full text-sm font-bold bg-emerald-100 text-emerald-900 border border-emerald-200'
            : 'px-3 py-1 rounded-full text-sm font-bold bg-amber-100 text-amber-900 border border-amber-200';
    }

    if (progressBar) {
        progressBar.style.width = `${pct}%`;
        progressBar.className = `h-2.5 rounded-full transition-all duration-300 ${valInfo.isAllValid ? 'bg-emerald-500' : 'bg-amber-500'}`;
    }

    if (jumpFirstBtn) {
        if (countMissing > 0) {
            jumpFirstBtn.classList.remove('hidden');
        } else {
            jumpFirstBtn.classList.add('hidden');
        }
    }

    if (!bodyEl) return;

    let sectionsHtml = '';
    if (countMissing > 0) {
        sectionsHtml += `
            <div>
                <h4 class="font-bold text-red-700 text-sm mb-2.5 flex items-center gap-1.5">
                    <iconify-icon icon="mdi:alert-circle" class="text-lg"></iconify-icon>
                    <span>Các trường chưa điền hoặc chưa hợp lệ (${countMissing}):</span>
                </h4>
                <div class="space-y-2.5">
                    ${valInfo.missing.map(m => `
                        <div class="p-3.5 bg-red-50/60 border border-red-200 rounded-xl flex items-center justify-between gap-3 hover:bg-red-50 transition-colors">
                            <div class="min-w-0">
                                <p class="font-bold text-red-950 text-sm">${escapeHtml(m.label)}</p>
                                <p class="text-sm text-red-800 mt-0.5 leading-snug">${escapeHtml(m.hint)}</p>
                            </div>
                            <button type="button" onclick="focusFieldTarget('${m.targetId}')" class="shrink-0 px-3.5 py-2 bg-red-600 hover:bg-red-700 text-white font-bold text-sm rounded-xl shadow-2xs transition-all cursor-pointer inline-flex items-center gap-1.5">
                                <span>Điền ngay</span>
                                <iconify-icon icon="mdi:arrow-right" class="text-base"></iconify-icon>
                            </button>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    if (valInfo.completed && valInfo.completed.length > 0) {
        sectionsHtml += `
            <div>
                <h4 class="font-bold text-emerald-800 text-sm mb-2.5 flex items-center gap-1.5">
                    <iconify-icon icon="mdi:check-circle" class="text-lg text-emerald-600"></iconify-icon>
                    <span>Các trường đã hoàn thành (${valInfo.completed.length}/16):</span>
                </h4>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    ${valInfo.completed.map(c => `
                        <button type="button" onclick="focusFieldTarget('${c.targetId}')" class="text-left p-2.5 bg-emerald-50/40 hover:bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-2 text-sm text-emerald-950 transition-colors cursor-pointer" title="Chuyển tới ${escapeHtml(c.label)}">
                            <iconify-icon icon="mdi:check-bold" class="text-emerald-600 text-base shrink-0"></iconify-icon>
                            <span class="font-semibold truncate">${escapeHtml(c.label)}</span>
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
    }

    bodyEl.innerHTML = sectionsHtml;
}

/**
 * Hiển thị Popup Modal tự viết chi tiết 16 trường dữ liệu bắt buộc (thay thế hoàn toàn SweetAlert2)
 */
function showMissingFieldsModal() {
    const valInfo = getMissingValidationFields();
    const modal = document.getElementById('missingFieldsModal');
    if (!modal) return;
    renderMissingFieldsModalContent(valInfo);
    modal.classList.remove('hidden');
}

function closeMissingFieldsModal() {
    const modal = document.getElementById('missingFieldsModal');
    if (modal) modal.classList.add('hidden');
}

function jumpToFirstMissingField() {
    const valInfo = getMissingValidationFields();
    if (valInfo.missing && valInfo.missing.length > 0) {
        focusFieldTarget(valInfo.missing[0].targetId);
    } else {
        closeMissingFieldsModal();
    }
}

let _isMissingFieldsBackdropMousedown = false;
function handleMissingFieldsBackdropMouseDown(e) {
    _isMissingFieldsBackdropMousedown = (e.target === e.currentTarget);
}
function handleMissingFieldsBackdropClick(e) {
    if (_isMissingFieldsBackdropMousedown && e.target === e.currentTarget) {
        closeMissingFieldsModal();
    }
    _isMissingFieldsBackdropMousedown = false;
}

// Export tường minh ra window để đảm bảo inline onclick luôn gọi được
window.showMissingFieldsModal = showMissingFieldsModal;
window.closeMissingFieldsModal = closeMissingFieldsModal;
window.jumpToFirstMissingField = jumpToFirstMissingField;
window.handleMissingFieldsBackdropMouseDown = handleMissingFieldsBackdropMouseDown;
window.handleMissingFieldsBackdropClick = handleMissingFieldsBackdropClick;

/**
 * Cuộn màn hình và focus tới ô nhập dữ liệu của trường được chọn
 */
function focusFieldTarget(targetId) {
    closeMissingFieldsModal();
    setTimeout(() => {
        let el = document.getElementById(targetId);
        if (!el) {
            el = document.querySelector(`[name="${targetId}"]`);
        }
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            if (typeof el.focus === 'function') {
                el.focus();
            }
            // Thêm viền phát sáng tạm thời
            el.classList.add('ring-4', 'ring-amber-400', 'transition-all');
            setTimeout(() => {
                el.classList.remove('ring-4', 'ring-amber-400');
            }, 2500);
        }
    }, 120);
}

// Export tường minh ra window
window.focusFieldTarget = focusFieldTarget;

function updateValidationState() {
    if (isBatchUpdating) return;
    
    const valInfo = getMissingValidationFields();
    const isAllValid = valInfo.isAllValid;
    const completedCount = valInfo.completedCount;
    const missingCount = valInfo.missing.length;

    // Nếu popup Chi tiết 16 trường đang mở thì tự động cập nhật trực tiếp
    const missingModal = document.getElementById('missingFieldsModal');
    if (missingModal && !missingModal.classList.contains('hidden')) {
        renderMissingFieldsModalContent(valInfo);
    }

    // Cập nhật Nút Xem chi tiết ở Footer
    const missingBtn = document.getElementById('btn-show-missing-fields');
    const missingBtnText = document.getElementById('missing-fields-btn-text');
    if (missingBtn && missingBtnText) {
        if (isAllValid) {
            missingBtn.className = 'inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-sm font-bold rounded-lg border border-emerald-300 transition-all cursor-pointer shadow-2xs ml-1';
            missingBtnText.textContent = 'Xem chi tiết (16/16)';
        } else {
            missingBtn.className = 'inline-flex items-center gap-1.5 px-3 py-1 bg-amber-100 hover:bg-amber-200 text-amber-900 text-sm font-bold rounded-lg border border-amber-300 transition-all cursor-pointer shadow-2xs ml-1';
            missingBtnText.textContent = `Xem chi tiết (${missingCount} trường thiếu)`;
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

    // 0. Kiểm tra tính hợp lệ của 16 trường Single Source of Truth trên biểu mẫu hiện tại
    const valInfo = getMissingValidationFields();
    if (!valInfo.isAllValid) {
        showMissingFieldsModal();
        return;
    }

    // Nếu đang có danh sách sản phẩm hàng loạt (> 1 sản phẩm)
    if (state.selectedBulkProducts && state.selectedBulkProducts.length > 1) {
        await startBulkCreationWorkflow();
        return;
    }

    // 1. Chuẩn bị payload đầy đủ
    const title = (document.getElementById('product-title')?.value || '').trim();
    const handle = (document.getElementById('product-handle')?.value || '').trim();
    const desc = (document.getElementById('product-desc')?.value || '').trim();
    const productType = (document.getElementById('product-type')?.value || '').trim();
    const categoryId = (document.getElementById('selected-category-id')?.value || '').trim();
    const categoryName = (document.getElementById('selected-category-name')?.value || state.selectedCategoryName || '').trim();
    const status = (document.getElementById('product-status')?.value || 'DRAFT').trim();
    const vendor = (document.getElementById('product-vendor')?.value || 'Wrydeco').trim();
    const seoTitle = (document.getElementById('seo-title')?.value || '').trim();
    const seoDesc = (document.getElementById('seo-desc')?.value || '').trim();
    const authorId = (document.getElementById('selected-author-id')?.value || '').trim();
    const authorObj = (state.authors || []).find(a => a.id === authorId) || state.selectedAuthorData || null;
    const authorName = authorObj ? String(authorObj.name || authorObj.displayName || '').trim() : '';
    const richDesc = (document.getElementById('rich-description')?.value || '').trim();
    const aeoHtml = (document.getElementById('aeo-html')?.value || '').trim();

    const checkedInterior = Array.from(document.querySelectorAll('input[name="interior_style"]:checked')).map(cb => cb.value);
    const checkedRoom = Array.from(document.querySelectorAll('input[name="room_type"]:checked')).map(cb => cb.value);

    // Variants & Options mapping (chỉ gửi các biến thể đang bật và giá trị option được sử dụng)
    const { optionsPayload, variantsPayload } = buildPrunedOptionsAndVariantsFromState();

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
                fileName: m.file.name || `image_${idx + 1}`,
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
        categoryName,
        status,
        vendor,
        tags: state.tags,
        seo: {
            title: seoTitle,
            description: seoDesc
        },
        authorId,
        authorName,
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
        await prepareProductImageCache([payloadObj], (done, total) => {
            if (btnText) btnText.textContent = `Đang lưu nguồn ảnh: ${done}/${total}...`;
        });
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
        refreshLatestArchiveSummary();

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
    const cleanText = String(text || '').replace(/^\uFEFF/, '');
    const rows = [];
    let currentRow = [];
    let currentField = '';
    let inQuotes = false;
    const len = cleanText.length;

    for (let i = 0; i < len; i++) {
        const char = cleanText[i];
        const nextChar = (i + 1 < len) ? cleanText[i + 1] : '';

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

/**
 * Trích xuất các dòng thực sự chứa dữ liệu biến thể từ CSV của 1 sản phẩm,
 * tự động loại bỏ các dòng phụ chỉ chứa ảnh gallery (image-only rows chuẩn Shopify CSV).
 */
function extractVariantRowsFromCsv(allRows) {
    if (!Array.isArray(allRows) || allRows.length === 0) return [];
    return allRows.filter((r, idx) => {
        if (idx === 0) return true;
        const hasOptVal = !!(
            (r['Option1 Value'] || '').trim() ||
            (r['Option2 Value'] || '').trim() ||
            (r['Option3 Value'] || '').trim()
        );
        const hasVariantFields = !!(
            (r['Variant Price'] || '').trim() ||
            (r['Variant SKU'] || '').trim() ||
            (r['Variant Barcode'] || '').trim() ||
            (r['Variant Barcodes'] || '').trim()
        );
        return hasOptVal || hasVariantFields;
    });
}

/**
 * Sinh mã Barcode dự phòng 12 chữ số ổn định (deterministic) dựa trên handle và chỉ số biến thể
 * khi cột Variant Barcode trong CSV để trống, đảm bảo duy nhất và đồng nhất giữa Form & Bulk.
 */
function generateFallbackBarcode(handle, variantIdx) {
    const str = String(handle || 'wrydeco-product').toLowerCase();
    let hash = 2166136261;
    for (let i = 0; i < str.length; i++) {
        hash ^= str.charCodeAt(i);
        hash = Math.imul(hash, 16777619);
    }
    const sixDigits = String((hash >>> 0) % 900000 + 100000);
    const seqDigits = String((variantIdx || 0) + 1).padStart(3, '0');
    return `893${sixDigits}${seqDigits}`;
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
        const variantCount = extractVariantRowsFromCsv(p.rows).length;
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
                                ${variantCount} biến thể
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
        
        const cachedTaxId = categoryVal ? state.taxonomyCacheByPath[categoryVal] : null;
        catIdInput.value = firstRow['Product Category ID'] || cachedTaxId || 'gid://shopify/TaxonomyCategory/hg-3-47';
        state.selectedCategoryId = catIdInput.value;

        // Chạy ngầm tra cứu taxonomy ID ở background mà KHÔNG dùng await chặn luồng chính
        if (!firstRow['Product Category ID'] && !cachedTaxId) {
            try {
                const parts = categoryVal.split('>');
                const leafName = parts[parts.length - 1].trim() || 'Shelf';
                fetch(`/api/taxonomy?search=${encodeURIComponent(leafName)}`)
                    .then(res => res.json())
                    .then(taxData => {
                        if (taxData && taxData.nodes && taxData.nodes.length > 0) {
                            const resolvedId = taxData.nodes[0].id;
                            catIdInput.value = resolvedId;
                            state.selectedCategoryId = resolvedId;
                            if (categoryVal) {
                                state.taxonomyCacheByPath[categoryVal] = resolvedId;
                                // Đồng bộ luôn Taxonomy ID cho các sản phẩm cùng danh mục trong Bulk Queue
                                if (Array.isArray(state.selectedBulkProducts)) {
                                    state.selectedBulkProducts.forEach(bp => {
                                        const rawProd = parsedCsvProducts ? parsedCsvProducts[bp.handle] : null;
                                        if (rawProd && rawProd.firstRow && rawProd.firstRow['Product Category'] === categoryVal && bp.payload) {
                                            bp.payload.categoryId = resolvedId;
                                        }
                                    });
                                }
                            }
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

    // 9. Biến thể (Options & Sparse Variant Matrix)
    // Chỉ trích xuất từ các dòng thực sự chứa dữ liệu biến thể (bỏ qua dòng chỉ chứa ảnh phụ)
    const variantRows = extractVariantRowsFromCsv(allRows);
    state.showDisabledVariants = false;

    const detectedOptions = [];
    for (let optNum = 1; optNum <= 3; optNum++) {
        const optName = firstRow[`Option${optNum} Name`];
        if (optName && optName.trim()) {
            const uniqueVals = [];
            variantRows.forEach(r => {
                const val = (r[`Option${optNum} Value`] || '').trim();
                if (val && !uniqueVals.some(u => u.toLowerCase() === val.toLowerCase())) {
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
            enabled: true,
            price: p.toFixed(2),
            compareAtPrice: c.toFixed(2),
            sku: firstRow['Variant SKU'] || `WRY-${handle.toUpperCase().slice(0, 8)}-1`,
            barcode: firstRow['Variant Barcode'] || firstRow['Variant Barcodes'] || generateFallbackBarcode(handle, 0)
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

        // Mặc định đánh dấu toàn bộ tổ hợp Cartesian là enabled = false trước,
        // sau đó chỉ bật enabled = true cho đúng những tổ hợp thực sự tồn tại trong CSV (Sparse Variants)
        const optIdArrays = state.options.map(o => o.values.map(v => v.clientId));
        const allCartCombs = optIdArrays.reduce((acc, curr) => {
            const res = [];
            acc.forEach(a => curr.forEach(c => res.push([...a, c])));
            return res;
        }, [[]]);

        allCartCombs.forEach(idArr => {
            const k = idArr.join('_');
            state.variantsByKey[k] = {
                enabled: false,
                price: '',
                compareAtPrice: '',
                sku: '',
                barcode: ''
            };
        });

        // Duyệt từng dòng variant thực tế trong CSV để bật enabled = true và map chính xác giá, SKU, Barcode
        variantRows.forEach((r, rowIdx) => {
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
                const rawP = parseFloat(r['Variant Price']);
                const priceNum = !isNaN(rawP) ? rawP : 129.00;
                let compareNum = parseFloat(r['Variant Compare At Price']) || 0;
                
                // Quy tắc: Compare At Price phải > Price
                if (compareNum <= priceNum) {
                    compareNum = Math.round(priceNum * 1.25);
                }

                state.variantsByKey[combKey] = {
                    enabled: true,
                    price: priceNum.toFixed(2),
                    compareAtPrice: compareNum.toFixed(2),
                    sku: (r['Variant SKU'] || '').trim() || `WRY-${handle.toUpperCase().slice(0, 8)}-${rowIdx + 1}`,
                    barcode: (r['Variant Barcode'] || r['Variant Barcodes'] || '').trim() || generateFallbackBarcode(handle, rowIdx)
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
            authorVal = (firstRow[k] || '').trim();
            break;
        }
    }
    let matchedAuthor = null;
    if (authorVal) {
        if (authorVal.startsWith('gid://shopify/Metaobject/')) {
            matchedAuthor = (state.authors || []).find(a => a.id === authorVal || (a.id && a.id.endsWith(authorVal.split('/').pop())));
        }
        if (!matchedAuthor && state.authors && state.authors.length > 0) {
            const cleanAuthor = authorVal.toLowerCase().replace(/[^a-z0-9]/g, '');
            matchedAuthor = state.authors.find(a => {
                const aId = (a.id || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                const aHandle = (a.handle || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                const aName = (a.name || a.displayName || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                return aId.includes(cleanAuthor) || aHandle.includes(cleanAuthor) || cleanAuthor.includes(aHandle) || aName.includes(cleanAuthor);
            });
        }
    }
    if (!matchedAuthor && state.authors && state.authors.length > 0) {
        matchedAuthor = state.authors[0];
    }
    if (matchedAuthor) {
        selectInlineAuthor(matchedAuthor.id);
    } else if (authorVal && authorVal.startsWith('gid://shopify/Metaobject/')) {
        state.selectedAuthorId = authorVal;
        const hiddenInput = document.getElementById('selected-author-id');
        if (hiddenInput) hiddenInput.value = authorVal;
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
        const missingModal = document.getElementById('missingFieldsModal');
        if (missingModal && !missingModal.classList.contains('hidden')) {
            closeMissingFieldsModal();
        }
        const archiveModal = document.getElementById('latestArchiveModal');
        if (archiveModal && !archiveModal.classList.contains('hidden')) {
            closeLatestArchiveModal();
        }
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
    const categoryVal = firstRow['Product Category'] || '';
    const categoryId = firstRow['Product Category ID'] || (categoryVal ? state.taxonomyCacheByPath[categoryVal] : '') || 'gid://shopify/TaxonomyCategory/hg-3-47';
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
            authorVal = (firstRow[k] || '').trim();
            break;
        }
    }
    if (authorVal) {
        if (authorVal.startsWith('gid://shopify/Metaobject/')) {
            authorId = authorVal;
        } else if (state.authors && state.authors.length > 0) {
            const cleanAuthor = authorVal.toLowerCase().replace(/[^a-z0-9]/g, '');
            const matched = state.authors.find(a => {
                const aId = (a.id || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                const aHandle = (a.handle || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                const aName = (a.name || a.displayName || '').toLowerCase().replace(/[^a-z0-9]/g, '');
                return aId.includes(cleanAuthor) || aHandle.includes(cleanAuthor) || cleanAuthor.includes(aHandle) || aName.includes(cleanAuthor);
            });
            if (matched) authorId = matched.id;
        }
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

    // Options & Sparse Variants (lọc bỏ các dòng chỉ chứa ảnh phụ)
    const variantRows = extractVariantRowsFromCsv(allRows);
    const detectedOptions = [];
    for (let optNum = 1; optNum <= 3; optNum++) {
        const optName = firstRow[`Option${optNum} Name`];
        if (optName && optName.trim()) {
            const uniqueVals = [];
            variantRows.forEach(r => {
                const val = (r[`Option${optNum} Value`] || '').trim();
                if (val && !uniqueVals.some(u => u.toLowerCase() === val.toLowerCase())) {
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
            sku: (firstRow['Variant SKU'] || '').trim() || `WRY-${h.toUpperCase().slice(0, 8)}-1`,
            barcode: (firstRow['Variant Barcode'] || firstRow['Variant Barcodes'] || '').trim() || generateFallbackBarcode(h, 0)
        }];
    } else {
        const seenCombKeys = new Set();
        const usedPerOpt = detectedOptions.map(() => new Set());

        variantRows.forEach((r, rowIdx) => {
            const optVals = [];
            const keyParts = [];
            for (let i = 0; i < detectedOptions.length; i++) {
                const optNum = i + 1;
                const rawLabel = (r[`Option${optNum} Value`] || '').trim();
                const canonicalVal = detectedOptions[i].values.find(u => u.toLowerCase() === rawLabel.toLowerCase()) || rawLabel;
                if (!canonicalVal) return;
                optVals.push({
                    optionName: detectedOptions[i].name,
                    name: canonicalVal
                });
                keyParts.push(canonicalVal.toLowerCase());
            }

            if (optVals.length !== detectedOptions.length) return;
            const combKey = keyParts.join('||');
            if (seenCombKeys.has(combKey)) return;
            seenCombKeys.add(combKey);

            optVals.forEach((ov, idx) => usedPerOpt[idx].add(ov.name.toLowerCase()));

            const rawP = parseFloat(r['Variant Price']);
            const pNum = !isNaN(rawP) ? rawP : 129.00;
            let cNum = parseFloat(r['Variant Compare At Price']) || 0;
            if (cNum <= pNum) cNum = Math.round(pNum * 1.25);

            variantsPayload.push({
                optionValues: optVals,
                price: pNum.toFixed(2),
                compareAtPrice: cNum.toFixed(2),
                sku: (r['Variant SKU'] || '').trim() || `WRY-${h.toUpperCase().slice(0, 8)}-${rowIdx + 1}`,
                barcode: (r['Variant Barcode'] || r['Variant Barcodes'] || '').trim() || generateFallbackBarcode(h, rowIdx)
            });
        });

        optionsPayload = detectedOptions.map((opt, idx) => ({
            name: opt.name,
            values: opt.values
                .filter(val => usedPerOpt[idx].has(val.toLowerCase()))
                .map(val => ({ label: val }))
        })).filter(opt => opt.values.length > 0);
    }

    const matchedAuthorObj = (state.authors || []).find(a => a.id === authorId) || null;
    const authorName = matchedAuthorObj ? String(matchedAuthorObj.name || matchedAuthorObj.displayName || '').trim() : '';

    return {
        store_type: state.currentStoreType,
        title,
        handle: h,
        descriptionHtml: desc,
        productType,
        categoryId,
        categoryName: categoryVal || 'Furniture > Shelving',
        status,
        vendor,
        tags,
        seo: {
            title: seoTitle,
            description: seoDesc
        },
        authorId,
        authorName,
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
 * Trích xuất toàn bộ dữ liệu hiện tại trên form thành payload chuẩn (chỉ lấy các biến thể đang bật)
 */
function collectCurrentFormPayload() {
    const title = (document.getElementById('product-title')?.value || '').trim();
    const handle = (document.getElementById('product-handle')?.value || '').trim();
    const desc = (document.getElementById('product-desc')?.value || '').trim();
    const productType = (document.getElementById('product-type')?.value || '').trim();
    const categoryId = (document.getElementById('selected-category-id')?.value || state.selectedCategoryId || '').trim();
    const categoryName = (document.getElementById('selected-category-name')?.value || state.selectedCategoryName || '').trim();
    const status = document.getElementById('product-status')?.value || 'DRAFT';
    const vendor = document.getElementById('product-vendor')?.value || 'Wrydeco';
    const seoTitle = (document.getElementById('seo-title')?.value || '').trim();
    const seoDesc = (document.getElementById('seo-desc')?.value || '').trim();
    const authorId = (document.getElementById('selected-author-id')?.value || state.selectedAuthorId || '').trim();
    const effAuthorId = authorId || (state.authors && state.authors.length > 0 ? state.authors[0].id : 'gid://shopify/Metaobject/default-author');
    const effAuthorObj = (state.authors || []).find(a => a.id === effAuthorId) || state.selectedAuthorData || null;
    const authorName = effAuthorObj ? String(effAuthorObj.name || effAuthorObj.displayName || '').trim() : '';
    const richDesc = (document.getElementById('rich-description')?.value || '').trim();
    const aeoHtml = (document.getElementById('aeo-html')?.value || '').trim();

    const checkedInterior = Array.from(document.querySelectorAll('input[name="interior_style"]:checked')).map(cb => cb.value);
    const checkedRoom = Array.from(document.querySelectorAll('input[name="room_type"]:checked')).map(cb => cb.value);

    // Chỉ lấy các biến thể đang bật và giá trị option được sử dụng thực tế (Sparse Variants)
    const { optionsPayload, variantsPayload } = buildPrunedOptionsAndVariantsFromState();

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
        categoryName: categoryName || '',
        status,
        vendor: vendor || 'Wrydeco',
        tags: state.tags || [],
        seo: {
            title: seoTitle || (title ? `${title} | Wrydeco` : ''),
            description: seoDesc || (title ? `Khám phá ${title} chất lượng cao từ Wrydeco.` : '')
        },
        authorId: effAuthorId,
        authorName,
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
async function prepareProductImageCache(payloads, onProgress = () => {}) {
    const sources = [...new Set(payloads.flatMap(p => (p.media || [])
        .filter(m => m.kind !== 'device' && m.url).map(m => m.url)))];
    if (!sources.length) return;
    const check = await fetch('/api/products/media-cache/check', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sources })
    });
    const info = await check.json();
    if (!check.ok || !info.success) throw new Error(info.error || 'Không thể kiểm tra nguồn ảnh.');
    const cached = new Set(info.cached || []);
    const pending = sources.filter(url => !cached.has(url));
    let next = 0;
    let completed = sources.length - pending.length;
    onProgress(completed, sources.length);
    const preserve = async () => {
        while (next < pending.length) {
            const url = pending[next++];
            const response = await fetch(url, { cache: 'force-cache', credentials: 'omit' });
            if (!response.ok) throw new Error(`Chưa lưu được nguồn ảnh (HTTP ${response.status}): ${url}. Chưa tạo sản phẩm nào.`);
            const blob = await response.blob();
            const body = new FormData();
            body.append('source_url', url);
            body.append('image', blob, 'import-image');
            const upload = await fetch('/api/products/media-cache', { method: 'POST', body });
            const result = await upload.json();
            if (!upload.ok || !result.success) throw new Error(result.error || 'Không thể lưu dữ liệu ảnh.');
            onProgress(++completed, sources.length);
        }
    };
    await Promise.all(Array.from({ length: Math.min(3, pending.length) }, preserve));
}


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

    // Reset modal header về trạng thái đang chạy
    setBulkProgressModalHeaderState('RUNNING', count, 0, 0);

    // Khóa nút đóng khi đang thực thi
    state.isBulkJobRunning = true;
    if (closeBtn) closeBtn.disabled = true;
    if (doneBtn) doneBtn.classList.add('hidden');

    // Reset giao diện Progress
    if (progressBar) progressBar.style.width = '0%';
    if (progressPercent) progressPercent.textContent = `0/${state.selectedBulkProducts.length} (0%)`;
    if (summaryBadge) {
        summaryBadge.textContent = 'Đang khởi tạo Bulk Job...';
        summaryBadge.className = 'text-sm font-semibold px-3 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded-full';
    }

    // Render bảng tiến trình ban đầu
    renderBulkProgressModalTableRows(state.selectedBulkProducts.map((item, idx) => ({
        item_index: idx,
        handle: item.handle,
        title: item.title,
        status: 'QUEUED',
        links: null,
        errors: null,
        error_message: null
    })));

    progressModal.classList.remove('hidden');

    try {
        // Step 1: Chuẩn bị Bulk Job
        const payloadList = state.selectedBulkProducts.map(item => item.payload);
        await prepareProductImageCache(payloadList, (done, total) => {
            if (summaryBadge) summaryBadge.textContent = `Đang lưu nguồn ảnh: ${done}/${total}. Sản phẩm chưa được tạo.`;
        });
        const prepResp = await fetch('/api/products/bulk-jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                store_type: state.currentStoreType,
                items: payloadList,
                products: payloadList
            })
        });

        const prepText = await prepResp.text();
        let prepResult;
        try {
            prepResult = JSON.parse(prepText);
        } catch (e) {
            throw new Error(`Máy chủ chuẩn bị phản hồi không hợp lệ (${prepResp.status}): ${prepText.slice(0, 160)}`);
        }

        if (!prepResp.ok || !prepResult.success) {
            throw new Error(prepResult.error || 'Không thể chuẩn bị Bulk Job');
        }

        const jobId = prepResult.job_id || (prepResult.job && prepResult.job.job_id);

        // Xóa cờ ẩn cũ trong localStorage để luôn hiện section inline cho Job mới
        try {
            localStorage.removeItem(`wrydeco_dismissed_bulk_job_${state.currentStoreType}`);
        } catch (e) {}

        // Khởi tạo snapshot ban đầu từ kết quả prepare (cập nhật ngay các dòng FAILED_VALIDATION nếu có)
        const initialItems = (prepResult.items || []).map((it, idx) => ({
            item_id: it.item_id || `${jobId}:${idx}`,
            item_index: typeof it.item_index === 'number' ? it.item_index : idx,
            handle: it.handle || (state.selectedBulkProducts[idx] && state.selectedBulkProducts[idx].handle) || '',
            title: it.title || (state.selectedBulkProducts[idx] && state.selectedBulkProducts[idx].title) || '',
            status: it.status || 'QUEUED',
            error_code: it.error_code || null,
            error_message: it.error_message || null,
            errors: it.errors || (it.error_message ? [{ field: 'validation', code: it.error_code || 'VALIDATION_ERROR', message: it.error_message }] : []),
            links: null,
            product_id: null
        }));

        const preFailedCount = initialItems.filter(it => isBulkStatusFailed(it.status)).length;
        state.currentBulkJobSnapshot = {
            job_id: jobId,
            store_type: state.currentStoreType,
            status: 'RUNNING',
            total_items: state.selectedBulkProducts.length,
            completed_items: preFailedCount,
            success_items: 0,
            failed_items: preFailedCount,
            created_at: new Date().toISOString(),
            items: initialItems
        };
        state.bulkInlineFilter = 'all';

        // Cập nhật ngay các dòng bị FAILED_VALIDATION trên Modal tiến trình
        initialItems.forEach((it, idx) => {
            updateSingleBulkProgressRowDOM(idx, it);
            syncSelectedBulkProductItemFromSnapshot(idx, it);
        });
        refreshLatestArchiveSummary();

        // Nếu tất cả sản phẩm đều lỗi ngay từ bước validate preflight thì kết thúc sớm
        if (preFailedCount >= state.selectedBulkProducts.length) {
            state.isBulkJobRunning = false;
            state.currentBulkJobSnapshot.status = 'COMPLETED_WITH_ERRORS';
            if (closeBtn) closeBtn.disabled = false;
            if (doneBtn) doneBtn.classList.remove('hidden');
            setBulkProgressModalHeaderState('COMPLETED_WITH_ERRORS', state.selectedBulkProducts.length, 0, preFailedCount);
            if (progressBar) progressBar.style.width = '100%';
            if (progressPercent) progressPercent.textContent = `${preFailedCount}/${state.selectedBulkProducts.length} (100%)`;
            if (summaryBadge) {
                summaryBadge.textContent = `Hoàn thành: 0 thành công, ${preFailedCount} lỗi dữ liệu`;
                summaryBadge.className = 'text-sm font-semibold px-3 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full';
            }
            return;
        }

        // Step 2: Bắt đầu chạy Worker
        const startResp = await fetch(`/api/products/bulk-jobs/${encodeURIComponent(jobId)}/start`, {
            method: 'POST'
        });
        const startText = await startResp.text();
        let startResult;
        try {
            startResult = JSON.parse(startText);
        } catch (e) {
            throw new Error(`Máy chủ kích hoạt phản hồi không hợp lệ (${startResp.status}): ${startText.slice(0, 160)}`);
        }

        if (!startResp.ok || !startResult.success) {
            throw new Error(startResult.error || 'Không thể kích hoạt Bulk Job Worker');
        }

        // Step 3: Kết nối Server-Sent Events theo dõi tiến trình
        connectBulkJobEventSource(jobId, state.selectedBulkProducts.length, preFailedCount);

    } catch (err) {
        state.isBulkJobRunning = false;
        refreshLatestArchiveSummary();
        if (summaryBadge) {
            summaryBadge.textContent = 'Lỗi khởi tạo: ' + err.message;
            summaryBadge.className = 'text-sm font-semibold px-3 py-1 bg-red-50 text-red-700 border border-red-200 rounded-full';
        }
        if (closeBtn) closeBtn.disabled = false;
        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'error',
                title: 'Khởi tạo thất bại',
                text: err.message
            });
        }
    }
}

/**
 * Kiểm tra trạng thái lỗi của một item trong Bulk Job
 */
function isBulkStatusFailed(status) {
    const st = String(status || '').toUpperCase();
    return st === 'FAILED' || st === 'FAILED_VALIDATION' || st === 'ERROR';
}

/**
 * Chuẩn hóa chuỗi thông báo lỗi đầy đủ của một item Bulk Job (không cắt cụt)
 */
function formatBulkItemErrors(itemOrEvent) {
    if (!itemOrEvent) return 'Tạo sản phẩm thất bại';
    const errs = Array.isArray(itemOrEvent.errors) ? itemOrEvent.errors : [];
    if (errs.length > 0) {
        const formatted = errs
            .map(e => {
                if (!e) return '';
                if (typeof e === 'string') return e;
                const msg = (e.message || '').trim();
                const field = (e.field || '').trim();
                if (!msg) return '';
                if (field && field !== 'unknown' && field !== 'worker' && !msg.toLowerCase().includes(field.toLowerCase())) {
                    return `[${field}] ${msg}`;
                }
                return msg;
            })
            .filter(Boolean);
        if (formatted.length > 0) {
            return formatted.join(' • ');
        }
    }
    if (itemOrEvent.error_message) return String(itemOrEvent.error_message);
    if (itemOrEvent.error) return String(itemOrEvent.error);
    return 'Tạo sản phẩm thất bại';
}

/**
 * Xác định chính xác chỉ số dòng (0-based index) của sự kiện SSE từ item_index, item_id ("job_xxx:idx") hoặc handle
 */
function resolveBulkEventItemIndex(data) {
    if (!data) return -1;
    if (typeof data.item_index === 'number' && !Number.isNaN(data.item_index)) {
        return data.item_index;
    }
    if (typeof data.item_id === 'string' && data.item_id.includes(':')) {
        const tail = data.item_id.split(':').pop();
        const parsed = parseInt(tail, 10);
        if (!Number.isNaN(parsed)) {
            return parsed;
        }
    }
    if (data.handle) {
        const targetHandle = String(data.handle).trim().toLowerCase();
        if (state.currentBulkJobSnapshot && Array.isArray(state.currentBulkJobSnapshot.items)) {
            const snapIdx = state.currentBulkJobSnapshot.items.findIndex(
                it => String(it.handle || '').trim().toLowerCase() === targetHandle
            );
            if (snapIdx >= 0) return snapIdx;
        }
        if (Array.isArray(state.selectedBulkProducts)) {
            const selIdx = state.selectedBulkProducts.findIndex(
                it => String(it.handle || '').trim().toLowerCase() === targetHandle
            );
            if (selIdx >= 0) return selIdx;
        }
    }
    return -1;
}

/**
 * Render lại danh sách dòng trong bảng của Popup Tiến trình (#bulk-progress-table-body)
 */
function renderBulkProgressModalTableRows(items) {
    const tbody = document.getElementById('bulk-progress-table-body');
    if (!tbody) return;
    const list = Array.isArray(items) ? items : [];
    tbody.innerHTML = list.map((item, idx) => {
        const rowIdx = typeof item.item_index === 'number' ? item.item_index : idx;
        return `
            <tr id="bulk-progress-row-${rowIdx}" class="hover:bg-gray-50/80 transition-colors">
                <td class="px-3.5 py-3 text-sm font-semibold text-gray-700 text-center">${rowIdx + 1}</td>
                <td class="px-3.5 py-3 text-sm font-mono text-gray-600 font-semibold truncate max-w-[160px]" title="${escapeHtml(item.handle || '')}">${escapeHtml(item.handle || '—')}</td>
                <td class="px-3.5 py-3 text-sm font-bold text-gray-900 truncate max-w-[200px]" title="${escapeHtml(item.title || '')}">${escapeHtml(item.title || '—')}</td>
                <td class="px-3.5 py-3 text-sm text-center whitespace-nowrap" id="bulk-progress-status-${rowIdx}"></td>
                <td class="px-3.5 py-3 text-sm" id="bulk-progress-result-${rowIdx}"></td>
            </tr>
        `;
    }).join('');

    list.forEach((item, idx) => {
        const rowIdx = typeof item.item_index === 'number' ? item.item_index : idx;
        updateSingleBulkProgressRowDOM(rowIdx, item);
    });
}

/**
 * Cập nhật DOM cho đúng 1 dòng trong Popup Tiến trình (#bulkProgressModal)
 */
function updateSingleBulkProgressRowDOM(idx, item) {
    if (idx < 0) return;
    const rowEl = document.getElementById(`bulk-progress-row-${idx}`);
    const statusEl = document.getElementById(`bulk-progress-status-${idx}`);
    const resultEl = document.getElementById(`bulk-progress-result-${idx}`);
    if (!statusEl || !resultEl) return;

    const st = String(item.status || 'QUEUED').toUpperCase();

    if (st === 'SUCCESS') {
        if (rowEl) rowEl.className = 'bg-emerald-50/20 hover:bg-emerald-50/50 transition-colors';
        statusEl.innerHTML = `
            <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-emerald-100 text-emerald-800">
                <iconify-icon icon="mdi:check-circle" class="text-sm text-emerald-600"></iconify-icon>
                <span>Thành công</span>
            </span>
        `;
        const links = item.links || {};
        resultEl.innerHTML = `
            <div class="flex items-center gap-2 flex-wrap">
                ${links.shopify_admin ? `<a href="${escapeHtml(links.shopify_admin)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 px-2.5 py-1 text-sm font-semibold bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"><iconify-icon icon="mdi:shopify"></iconify-icon>Admin</a>` : ''}
                ${links.storefront ? `<a href="${escapeHtml(links.storefront)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 px-2.5 py-1 text-sm font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg transition-colors"><iconify-icon icon="mdi:web"></iconify-icon>Storefront</a>` : ''}
                ${links.tool ? `<a href="${escapeHtml(links.tool)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-1 px-2.5 py-1 text-sm font-semibold bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded-lg transition-colors"><iconify-icon icon="mdi:open-in-new"></iconify-icon>Tool</a>` : ''}
            </div>
        `;
    } else if (isBulkStatusFailed(st)) {
        if (rowEl) rowEl.className = 'bg-red-50/40 hover:bg-red-50/70 transition-colors';
        const errText = formatBulkItemErrors(item);
        const badgeLabel = st === 'FAILED_VALIDATION' ? 'Lỗi dữ liệu' : 'Lỗi';
        statusEl.innerHTML = `
            <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-red-100 text-red-800" title="${escapeHtml(errText)}">
                <iconify-icon icon="mdi:alert-circle" class="text-sm text-red-600"></iconify-icon>
                <span>${badgeLabel}</span>
            </span>
        `;
        resultEl.innerHTML = `
            <div class="text-sm text-red-700 font-medium leading-snug break-words max-w-[340px]">${escapeHtml(errText)}</div>
        `;
    } else if (st === 'CREATING' || st === 'RUNNING') {
        if (rowEl) rowEl.className = 'bg-blue-50/30 transition-colors';
        statusEl.innerHTML = `
            <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-blue-100 text-blue-800 animate-pulse">
                <svg class="animate-spin h-3.5 w-3.5 text-blue-600" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Đang tạo...</span>
            </span>
        `;
        resultEl.innerHTML = `<span class="text-sm text-blue-600 font-medium">Đang gửi dữ liệu lên Shopify...</span>`;
    } else if (st === 'THROTTLED') {
        statusEl.innerHTML = `
            <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-amber-100 text-amber-800">
                <iconify-icon icon="mdi:speedometer-slow" class="text-sm"></iconify-icon>
                <span>Điều tiết (${escapeHtml(String(item.wait_seconds || 1))}s)...</span>
            </span>
        `;
    } else {
        if (rowEl) rowEl.className = 'hover:bg-gray-50/80 transition-colors';
        statusEl.innerHTML = `
            <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-semibold bg-gray-100 text-gray-600">
                <iconify-icon icon="mdi:clock-outline" class="text-sm"></iconify-icon>
                <span>Chờ tạo</span>
            </span>
        `;
        resultEl.innerHTML = `<span class="text-sm text-gray-400">—</span>`;
    }
}

/**
 * Đồng bộ trạng thái của item về danh sách selectedBulkProducts (phục vụ modal tổng quan)
 */
function syncSelectedBulkProductItemFromSnapshot(idx, item) {
    if (!Array.isArray(state.selectedBulkProducts) || !state.selectedBulkProducts[idx]) return;
    const st = String(item.status || '').toUpperCase();
    if (st === 'SUCCESS') {
        state.selectedBulkProducts[idx].status = 'SUCCESS';
        state.selectedBulkProducts[idx].links = item.links || null;
        state.selectedBulkProducts[idx].error = null;
    } else if (isBulkStatusFailed(st)) {
        state.selectedBulkProducts[idx].status = 'ERROR';
        state.selectedBulkProducts[idx].error = formatBulkItemErrors(item);
    } else if (st === 'CREATING' || st === 'RUNNING') {
        state.selectedBulkProducts[idx].status = 'RUNNING';
    } else {
        state.selectedBulkProducts[idx].status = 'PENDING';
    }
}

/**
 * Cập nhật tiêu đề, icon và ghi chú chân trang của Popup Tiến trình theo trạng thái Job
 */
function setBulkProgressModalHeaderState(jobStatus, total, successCount, failedCount) {
    const iconBox = document.getElementById('bulk-progress-icon-box');
    const titleEl = document.getElementById('bulk-progress-title');
    const subtitleEl = document.getElementById('bulk-progress-subtitle');
    const footerNote = document.getElementById('bulk-progress-footer-note');

    const st = String(jobStatus || 'RUNNING').toUpperCase();
    if (st === 'COMPLETED') {
        if (iconBox) {
            iconBox.className = 'w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shrink-0';
            iconBox.innerHTML = '<iconify-icon icon="mdi:check-decagram" class="text-2xl"></iconify-icon>';
        }
        if (titleEl) titleEl.textContent = `Đã tạo thành công ${successCount}/${total} sản phẩm!`;
        if (subtitleEl) subtitleEl.textContent = 'Toàn bộ kết quả và liên kết cũng đã được lưu tại bảng Kết quả ngay đầu trang.';
        if (footerNote) footerNote.textContent = 'Bạn có thể đóng popup này bất cứ lúc nào — kết quả vẫn hiển thị trực tiếp trên trang.';
    } else if (st === 'COMPLETED_WITH_ERRORS') {
        if (iconBox) {
            iconBox.className = 'w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0';
            iconBox.innerHTML = '<iconify-icon icon="mdi:alert-decagram-outline" class="text-2xl"></iconify-icon>';
        }
        if (titleEl) titleEl.textContent = `Hoàn tất: ${successCount} thành công, ${failedCount} sản phẩm gặp lỗi`;
        if (subtitleEl) subtitleEl.textContent = 'Chi tiết nguyên nhân lỗi của từng sản phẩm đã được hiển thị bên dưới và lưu cố định ở đầu trang.';
        if (footerNote) footerNote.textContent = 'Đóng popup để xem bảng chi tiết lỗi rộng rãi ngay trên trang và nạp sửa sản phẩm lỗi.';
    } else if (st === 'PAUSED_PROXY') {
        if (iconBox) {
            iconBox.className = 'w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0';
            iconBox.innerHTML = '<iconify-icon icon="mdi:pause-octagon-outline" class="text-2xl"></iconify-icon>';
        }
        if (titleEl) titleEl.textContent = 'Tiến trình tạm dừng an toàn do kết nối US Proxy';
        if (subtitleEl) subtitleEl.textContent = 'Các sản phẩm chưa xử lý vẫn được giữ an toàn trong hàng đợi.';
        if (footerNote) footerNote.textContent = 'Vui lòng kiểm tra kết nối US Proxy trước khi tiếp tục.';
    } else {
        if (iconBox) {
            iconBox.className = 'w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shrink-0';
            iconBox.innerHTML = '<iconify-icon icon="mdi:sync" class="text-2xl animate-spin"></iconify-icon>';
        }
        if (titleEl) titleEl.textContent = 'Đang tiến hành tạo sản phẩm hàng loạt...';
        if (subtitleEl) subtitleEl.textContent = 'Hệ thống đang gọi Shopify GraphQL API có kiểm soát tốc độ an toàn.';
        if (footerNote) footerNote.textContent = 'Đang lắng nghe sự kiện từ máy chủ theo thời gian thực...';
    }
}

/**
 * Tải snapshot chuẩn xác từ Server (/api/products/bulk-jobs/{jobId}) để đồng bộ 100% trạng thái mọi dòng
 */
async function syncBulkJobSnapshotFromServer(jobId, includePayload = false) {
    if (!jobId) return null;
    try {
        const resp = await fetch(`/api/products/bulk-jobs/${encodeURIComponent(jobId)}?include_payload=${includePayload ? 'true' : 'false'}`);
        if (!resp.ok) return null;
        const data = await resp.json();
        if (!data || !data.success || !data.job) return null;

        const serverJob = data.job;
        // Giữ lại payload cục bộ nếu bản tải nhẹ không đính kèm payload
        if (!includePayload && state.currentBulkJobSnapshot && Array.isArray(state.currentBulkJobSnapshot.items)) {
            const oldByIdx = new Map(state.currentBulkJobSnapshot.items.map(it => [it.item_index, it]));
            (serverJob.items || []).forEach(it => {
                const prev = oldByIdx.get(it.item_index);
                if (!it.payload && prev && prev.payload) {
                    it.payload = prev.payload;
                }
            });
        }

        state.currentBulkJobSnapshot = serverJob;

        const items = serverJob.items || [];
        const total = serverJob.total_items || items.length || 0;
        const successCount = typeof serverJob.success_items === 'number'
            ? serverJob.success_items
            : items.filter(it => String(it.status).toUpperCase() === 'SUCCESS').length;
        const failedCount = typeof serverJob.failed_items === 'number'
            ? serverJob.failed_items
            : items.filter(it => isBulkStatusFailed(it.status)).length;
        const finished = successCount + failedCount;
        const pct = total > 0 ? Math.min(100, Math.round((finished / total) * 100)) : 0;

        // Đồng bộ lại từng dòng trong Popup Tiến trình (nếu bảng đã có hoặc render mới)
        const modalTbody = document.getElementById('bulk-progress-table-body');
        if (modalTbody) {
            if (modalTbody.children.length !== items.length) {
                renderBulkProgressModalTableRows(items);
            } else {
                items.forEach((it, i) => {
                    const rowIdx = typeof it.item_index === 'number' ? it.item_index : i;
                    updateSingleBulkProgressRowDOM(rowIdx, it);
                });
            }
        }

        items.forEach((it, i) => {
            const rowIdx = typeof it.item_index === 'number' ? it.item_index : i;
            syncSelectedBulkProductItemFromSnapshot(rowIdx, it);
        });

        // Đồng bộ thanh progress trên Popup
        const progressBar = document.getElementById('bulk-progress-bar-fill') || document.getElementById('bulk-progress-bar');
        const progressPercent = document.getElementById('bulk-progress-percent');
        const summaryBadge = document.getElementById('bulk-progress-stats') || document.getElementById('bulk-summary-badge');
        if (progressBar) progressBar.style.width = `${pct}%`;
        if (progressPercent) progressPercent.textContent = `${finished}/${total} (${pct}%)`;

        const jobStatus = String(serverJob.status || '').toUpperCase();
        if (jobStatus === 'COMPLETED' || jobStatus === 'COMPLETED_WITH_ERRORS') {
            state.isBulkJobRunning = false;
            setBulkProgressModalHeaderState(jobStatus, total, successCount, failedCount);
            if (summaryBadge) {
                summaryBadge.textContent = `Hoàn thành: ${successCount} thành công, ${failedCount} lỗi`;
                summaryBadge.className = `text-sm font-semibold px-3 py-1 rounded-full ${failedCount === 0 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`;
            }
            const closeBtn = document.getElementById('btn-close-progress-modal');
            const doneBtn = document.getElementById('btn-progress-done');
            if (closeBtn) closeBtn.disabled = false;
            if (doneBtn) doneBtn.classList.remove('hidden');
        } else if (jobStatus === 'PAUSED_PROXY') {
            state.isBulkJobRunning = false;
            setBulkProgressModalHeaderState(jobStatus, total, successCount, failedCount);
        } else if (summaryBadge) {
            summaryBadge.textContent = `Đang xử lý: ${successCount} thành công, ${failedCount} lỗi`;
            summaryBadge.className = 'text-sm font-semibold px-3 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full';
        }

        return serverJob;
    } catch (err) {
        console.warn('syncBulkJobSnapshotFromServer error:', err);
        return null;
    }
}

/**
 * Kết nối Server-Sent Events (SSE) theo dõi tiến trình tạo sản phẩm hàng loạt
 */
function connectBulkJobEventSource(jobId, totalItems) {
    const initialFailedCount = arguments.length > 2 ? (arguments[2] || 0) : 0;
    const progressBar = document.getElementById('bulk-progress-bar-fill') || document.getElementById('bulk-progress-bar');
    const progressPercent = document.getElementById('bulk-progress-percent');
    const summaryBadge = document.getElementById('bulk-progress-stats') || document.getElementById('bulk-summary-badge');
    const closeBtn = document.getElementById('btn-close-progress-modal') || document.getElementById('btn-progress-done') || document.getElementById('btn-close-bulk-progress');
    const doneBtn = document.getElementById('btn-progress-done');

    if (state.bulkFallbackPollTimer) {
        clearInterval(state.bulkFallbackPollTimer);
        state.bulkFallbackPollTimer = null;
    }

    let completedCount = 0;
    let failedCount = initialFailedCount || 0;
    let hasHandledCompletion = false;

    const evtSource = new EventSource(`/api/products/bulk-jobs/${encodeURIComponent(jobId)}/events`);

    const updateProgress = () => {
        const finished = Math.min(totalItems, completedCount + failedCount);
        const pct = totalItems > 0 ? Math.min(100, Math.round((finished / totalItems) * 100)) : 0;
        if (progressBar) progressBar.style.width = `${pct}%`;
        if (progressPercent) progressPercent.textContent = `${finished}/${totalItems} (${pct}%)`;
        if (summaryBadge) {
            summaryBadge.textContent = `Đang xử lý: ${completedCount} thành công, ${failedCount} lỗi`;
            summaryBadge.className = 'text-sm font-semibold px-3 py-1 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full';
        }
        if (state.currentBulkJobSnapshot) {
            state.currentBulkJobSnapshot.completed_items = finished;
            state.currentBulkJobSnapshot.success_items = completedCount;
            state.currentBulkJobSnapshot.failed_items = failedCount;
        }
    };

    evtSource.addEventListener('job_started', () => {
        if (summaryBadge) {
            summaryBadge.textContent = 'Tiến trình đang chạy...';
        }
    });

    evtSource.addEventListener('item_started', (e) => {
        try {
            const data = JSON.parse(e.data);
            const idx = resolveBulkEventItemIndex(data);
            const itemObj = {
                item_index: idx,
                handle: data.handle,
                title: data.title,
                status: 'CREATING'
            };
            if (state.currentBulkJobSnapshot && state.currentBulkJobSnapshot.items && state.currentBulkJobSnapshot.items[idx]) {
                state.currentBulkJobSnapshot.items[idx].status = 'CREATING';
            }
            updateSingleBulkProgressRowDOM(idx, itemObj);
            syncSelectedBulkProductItemFromSnapshot(idx, itemObj);
        } catch (err) {
            console.warn('Error parsing item_started event', err);
        }
    });

    evtSource.addEventListener('item_throttled', (e) => {
        try {
            const data = JSON.parse(e.data);
            const idx = resolveBulkEventItemIndex(data);
            updateSingleBulkProgressRowDOM(idx, {
                item_index: idx,
                status: 'THROTTLED',
                wait_seconds: data.wait_seconds
            });
        } catch (err) {
            console.warn('Error parsing item_throttled event', err);
        }
    });

    evtSource.addEventListener('item_succeeded', (e) => {
        try {
            const data = JSON.parse(e.data);
            const idx = resolveBulkEventItemIndex(data);
            completedCount++;

            const updatedItem = {
                item_index: idx,
                handle: data.handle || (state.selectedBulkProducts[idx] && state.selectedBulkProducts[idx].handle) || '',
                title: data.title || (state.selectedBulkProducts[idx] && state.selectedBulkProducts[idx].title) || '',
                status: 'SUCCESS',
                product_id: data.product_id || null,
                links: data.links || {},
                errors: null,
                error_message: null
            };

            if (state.currentBulkJobSnapshot && state.currentBulkJobSnapshot.items && state.currentBulkJobSnapshot.items[idx]) {
                Object.assign(state.currentBulkJobSnapshot.items[idx], updatedItem);
            }
            updateSingleBulkProgressRowDOM(idx, updatedItem);
            syncSelectedBulkProductItemFromSnapshot(idx, updatedItem);
            updateProgress();
        } catch (err) {
            console.warn('Error parsing item_succeeded event', err);
        }
    });

    evtSource.addEventListener('item_failed', (e) => {
        try {
            const data = JSON.parse(e.data);
            const idx = resolveBulkEventItemIndex(data);
            failedCount++;

            const errMsg = formatBulkItemErrors(data);
            const updatedItem = {
                item_index: idx,
                handle: data.handle || (state.selectedBulkProducts[idx] && state.selectedBulkProducts[idx].handle) || '',
                title: data.title || (state.selectedBulkProducts[idx] && state.selectedBulkProducts[idx].title) || '',
                status: 'FAILED',
                error_code: data.error_code || (Array.isArray(data.errors) && data.errors[0] && data.errors[0].code) || 'CREATION_FAILED',
                error_message: errMsg,
                errors: Array.isArray(data.errors) ? data.errors : [{ field: 'error', message: errMsg }],
                links: null
            };

            if (state.currentBulkJobSnapshot && state.currentBulkJobSnapshot.items && state.currentBulkJobSnapshot.items[idx]) {
                Object.assign(state.currentBulkJobSnapshot.items[idx], updatedItem);
            }
            updateSingleBulkProgressRowDOM(idx, updatedItem);
            syncSelectedBulkProductItemFromSnapshot(idx, updatedItem);
            updateProgress();
        } catch (err) {
            console.warn('Error parsing item_failed event', err);
        }
    });

    evtSource.addEventListener('job_paused', async (e) => {
        try {
            const data = JSON.parse(e.data);
            state.isBulkJobRunning = false;
            evtSource.close();
            await syncBulkJobSnapshotFromServer(jobId, false);
            refreshLatestArchiveSummary();
            if (summaryBadge) {
                summaryBadge.textContent = 'Tạm dừng: Gặp sự cố kết nối US Proxy an toàn';
                summaryBadge.className = 'text-sm font-semibold px-3 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full';
            }
            if (closeBtn) closeBtn.disabled = false;
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: 'warning',
                    title: 'Tiến trình tạm dừng',
                    text: `Tiến trình đã tự động dừng an toàn để tránh làm hỏng các sản phẩm tiếp theo do lỗi US Proxy: ${data.proxy_error || data.message || data.reason || 'Lỗi mạng proxy'}`
                });
            }
        } catch (err) {
            console.warn('Error parsing job_paused event', err);
        }
    });

    evtSource.addEventListener('job_completed', async (e) => {
        if (hasHandledCompletion) return;
        hasHandledCompletion = true;
        try {
            const data = JSON.parse(e.data);
            state.isBulkJobRunning = false;
            evtSource.close();
            if (state.bulkFallbackPollTimer) {
                clearInterval(state.bulkFallbackPollTimer);
                state.bulkFallbackPollTimer = null;
            }

            // Đồng bộ snapshot chuẩn xác 100% từ SQLite trước khi hiển thị tổng kết
            const finalJob = await syncBulkJobSnapshotFromServer(jobId, false);
            refreshLatestArchiveSummary();

            const successTotal = finalJob
                ? finalJob.success_items
                : (data.success_items ?? data.success ?? data.completed_items ?? completedCount);
            const failedTotal = finalJob
                ? finalJob.failed_items
                : (data.failed_items ?? data.failed ?? failedCount);

            if (progressBar) progressBar.style.width = '100%';
            if (progressPercent) progressPercent.textContent = `${totalItems}/${totalItems} (100%)`;
            if (closeBtn) closeBtn.disabled = false;
            if (doneBtn) doneBtn.classList.remove('hidden');

            setBulkProgressModalHeaderState(
                failedTotal === 0 ? 'COMPLETED' : 'COMPLETED_WITH_ERRORS',
                totalItems,
                successTotal,
                failedTotal
            );

            if (summaryBadge) {
                summaryBadge.textContent = `Hoàn thành: ${successTotal} thành công, ${failedTotal} lỗi`;
                summaryBadge.className = `text-sm font-semibold px-3 py-1 rounded-full ${failedTotal === 0 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`;
            }

            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    icon: failedTotal === 0 ? 'success' : 'warning',
                    title: 'Hoàn tất tạo sản phẩm hàng loạt',
                    html: `
                        <div class="text-left text-sm text-gray-700 space-y-2">
                            <p>Đã xử lý xong toàn bộ <b>${totalItems}</b> sản phẩm.</p>
                            <p class="text-emerald-700 font-semibold">&bull; Thành công: <b>${successTotal}</b> sản phẩm</p>
                            ${failedTotal > 0 ? `<p class="text-red-600 font-semibold">&bull; Lỗi: <b>${failedTotal}</b> sản phẩm</p>` : ''}
                            <p class="text-gray-600 mt-2">Toàn bộ dữ liệu và kết quả chi tiết từng sản phẩm đã được lưu tự động vào <b>Bản lưu trữ tạo gần nhất</b> trên máy chủ để bạn xem lại hoặc chọn điền lên trang bất cứ lúc nào.</p>
                        </div>
                    `,
                    confirmButtonText: 'Đã hiểu'
                });
            }
        } catch (err) {
            console.warn('Error parsing job_completed event', err);
        }
    });

    evtSource.onerror = (err) => {
        console.warn('SSE EventSource error/closed:', err);
        evtSource.close();
        if (hasHandledCompletion) return;

        // Fallback Polling: Nếu kết nối SSE bị ngắt giữa chừng, tự động đồng bộ qua REST API mỗi 2 giây tới khi Job hoàn tất
        if (!state.bulkFallbackPollTimer) {
            state.bulkFallbackPollTimer = setInterval(async () => {
                const snap = await syncBulkJobSnapshotFromServer(jobId, false);
                if (!snap) return;
                const st = String(snap.status || '').toUpperCase();
                if (st === 'COMPLETED' || st === 'COMPLETED_WITH_ERRORS' || st === 'PAUSED_PROXY' || st === 'CANCELLED') {
                    hasHandledCompletion = true;
                    state.isBulkJobRunning = false;
                    clearInterval(state.bulkFallbackPollTimer);
                    state.bulkFallbackPollTimer = null;
                    if (closeBtn) closeBtn.disabled = false;
                    if (doneBtn) doneBtn.classList.remove('hidden');
                    refreshLatestArchiveSummary();
                }
            }, 2000);
        }
    };
}

/**
 * Kiểm tra xem có Bulk Job nào vẫn đang chạy nền khi vừa vào trang không để tự động kết nối SSE
 */
async function checkRunningBulkJobOnLoad() {
    try {
        const resp = await fetch(`/api/products/bulk-jobs/latest?store_type=${encodeURIComponent(state.currentStoreType)}&include_payload=false`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data || !data.success || !data.job) return;

        state.currentBulkJobSnapshot = data.job;

        // Nếu Job gần nhất vẫn đang chạy nền, tự động kết nối SSE để tiếp tục theo dõi
        if (String(data.job.status || '').toUpperCase() === 'RUNNING') {
            state.isBulkJobRunning = true;
            const preFailed = (data.job.items || []).filter(it => isBulkStatusFailed(it.status)).length;
            connectBulkJobEventSource(data.job.job_id, data.job.total_items || (data.job.items || []).length, preFailed);
        }
    } catch (err) {
        console.warn('checkRunningBulkJobOnLoad error:', err);
    }
}

/**
 * Mở lại Popup Tiến trình tạo hàng loạt
 */
function reopenBulkProgressModal() {
    const modal = document.getElementById('bulkProgressModal');
    if (!modal || !state.currentBulkJobSnapshot) return;

    const job = state.currentBulkJobSnapshot;
    const items = job.items || [];
    const total = job.total_items || items.length;
    const successCount = items.filter(it => String(it.status).toUpperCase() === 'SUCCESS').length;
    const failedCount = items.filter(it => isBulkStatusFailed(it.status)).length;
    const finished = Math.min(total, successCount + failedCount);
    const pct = total > 0 ? Math.min(100, Math.round((finished / total) * 100)) : 0;

    renderBulkProgressModalTableRows(items);
    setBulkProgressModalHeaderState(job.status, total, successCount, failedCount);

    const progressBar = document.getElementById('bulk-progress-bar-fill') || document.getElementById('bulk-progress-bar');
    const progressPercent = document.getElementById('bulk-progress-percent');
    const summaryBadge = document.getElementById('bulk-progress-stats') || document.getElementById('bulk-summary-badge');
    const closeBtn = document.getElementById('btn-close-progress-modal');
    const doneBtn = document.getElementById('btn-progress-done');

    if (progressBar) progressBar.style.width = `${pct}%`;
    if (progressPercent) progressPercent.textContent = `${finished}/${total} (${pct}%)`;
    if (summaryBadge) {
        summaryBadge.textContent = state.isBulkJobRunning
            ? `Đang xử lý: ${successCount} thành công, ${failedCount} lỗi`
            : `Hoàn thành: ${successCount} thành công, ${failedCount} lỗi`;
        summaryBadge.className = `text-sm font-semibold px-3 py-1 rounded-full ${failedCount === 0 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`;
    }
    if (closeBtn) closeBtn.disabled = !!state.isBulkJobRunning;
    if (doneBtn) {
        if (state.isBulkJobRunning) doneBtn.classList.add('hidden');
        else doneBtn.classList.remove('hidden');
    }

    modal.classList.remove('hidden');
}

/**
 * Đóng modal tiến trình tạo hàng loạt
 */
let _isBulkProgressMouseDownOnBackdrop = false;
function handleBulkProgressBackdropMouseDown(e) {
    _isBulkProgressMouseDownOnBackdrop = (e.target === e.currentTarget);
}
function handleBulkProgressBackdropClick(e) {
    if (_isBulkProgressMouseDownOnBackdrop && e.target === e.currentTarget && !state.isBulkJobRunning) {
        closeBulkProgressModal();
    }
    _isBulkProgressMouseDownOnBackdrop = false;
}

function closeBulkProgressModal() {
    const modal = document.getElementById('bulkProgressModal');
    if (modal) modal.classList.add('hidden');
}

/**
 * Điền trực tiếp một object payload chuẩn (lưu trong Bản lưu trữ tạo gần nhất JSON hoặc SQLite Bulk Job) lên form chỉnh sửa
 */
function populateFormFromPayloadObject(payload) {
    if (!payload || typeof payload !== 'object') return;

    isBatchUpdating = true;
    try {
        // 1. Phương tiện (Media)
        const rawMedia = Array.isArray(payload.media) ? payload.media : [];
        state.media = rawMedia
            .map(m => (typeof m === 'string' ? m.trim() : String((m && (m.url || m.previewUrl)) || '').trim()))
            .filter(Boolean)
            .map((url, idx) => ({
                id: 'med_' + Math.random().toString(36).substr(2, 9),
                kind: 'url',
                url,
                file: null,
                previewUrl: url,
                position: idx + 1
            }));
        renderMediaGallery();

        // 2. Tên sản phẩm (Title) & Đường dẫn URL (Handle)
        const titleVal = String(payload.title || '').trim();
        const titleEl = document.getElementById('product-title');
        if (titleEl) {
            titleEl.value = titleVal;
        }
        const titleCharCount = document.getElementById('title-char-count');
        if (titleCharCount) {
            titleCharCount.textContent = `${titleVal.length} ký tự`;
        }

        const rawHandle = String(payload.handle || '').trim();
        const handleVal = rawHandle || slugify(titleVal);
        const handleEl = document.getElementById('product-handle');
        const resetHandleBtn = document.getElementById('btn-reset-handle');
        if (handleEl) {
            handleEl.value = handleVal;
            if (rawHandle) {
                handleEl.setAttribute('data-touched', 'true');
                if (resetHandleBtn) resetHandleBtn.classList.remove('hidden');
            } else {
                handleEl.removeAttribute('data-touched');
                if (resetHandleBtn) resetHandleBtn.classList.add('hidden');
            }
        }
        const previewHandleSpan = document.getElementById('seo-preview-handle');
        if (previewHandleSpan) {
            previewHandleSpan.textContent = handleVal || 'sample-product';
        }

        // 3. Mô tả ngắn (Description) & Loại sản phẩm (Type)
        const descEl = document.getElementById('product-desc');
        if (descEl) descEl.value = payload.descriptionHtml || '';

        const typeEl = document.getElementById('product-type');
        if (typeEl) typeEl.value = payload.productType || '';

        // 4. Danh mục (Category): gán .value cho cả hidden input #selected-category-id VÀ text input #selected-category-name
        const catId = String(payload.categoryId || '').trim();
        let catName = String(payload.categoryName || '').trim();
        if (!catName && catId) {
            if (catId === 'gid://shopify/TaxonomyCategory/hg-3-47') {
                catName = 'Home & Garden > Lighting > Lamps (hg-3-47)';
            } else {
                catName = catId;
            }
        }
        state.selectedCategoryId = catId;
        state.selectedCategoryName = catName;
        const catIdInput = document.getElementById('selected-category-id');
        const catNameInput = document.getElementById('selected-category-name');
        if (catIdInput) catIdInput.value = catId;
        if (catNameInput) catNameInput.value = catName;

        // 5. Trạng thái (Status) & Nhà cung cấp (Vendor)
        const statusSelect = document.getElementById('product-status');
        if (statusSelect) {
            const normStatus = String(payload.status || 'DRAFT').trim().toUpperCase();
            statusSelect.value = (normStatus === 'ACTIVE' || normStatus === 'UNLISTED') ? normStatus : 'DRAFT';
            if (!statusSelect.value) statusSelect.value = 'DRAFT';
        }

        const vendorVal = String(payload.vendor || 'Wrydeco').trim() || 'Wrydeco';
        const vendorSelect = document.getElementById('product-vendor');
        if (vendorSelect) {
            let matchedVendor = false;
            for (let i = 0; i < vendorSelect.options.length; i++) {
                if (vendorSelect.options[i].value.toLowerCase() === vendorVal.toLowerCase()) {
                    vendorSelect.selectedIndex = i;
                    matchedVendor = true;
                    break;
                }
            }
            if (!matchedVendor) {
                const opt = document.createElement('option');
                opt.value = vendorVal;
                opt.textContent = vendorVal;
                opt.selected = true;
                vendorSelect.appendChild(opt);
            }
        }

        // 6. Thẻ sản phẩm (Tags)
        state.tags = Array.isArray(payload.tags) ? payload.tags.map(t => String(t).trim()).filter(Boolean) : [];
        renderTags();

        // 7. SEO Title & SEO Description + Google Preview
        const seo = (payload.seo && typeof payload.seo === 'object') ? payload.seo : {};
        const seoTitleVal = String(seo.title || (titleVal ? `${titleVal} | Wrydeco` : '')).trim();
        const seoDescVal = String(seo.description || '').trim();

        const seoTitleEl = document.getElementById('seo-title');
        if (seoTitleEl) {
            seoTitleEl.value = seoTitleVal;
            if (seoTitleVal) {
                seoTitleEl.setAttribute('data-touched', 'true');
            } else {
                seoTitleEl.removeAttribute('data-touched');
            }
        }
        const seoTitleCount = document.getElementById('seo-title-count');
        if (seoTitleCount) seoTitleCount.textContent = `${seoTitleVal.length} / 70 ký tự`;
        const seoPreviewTitle = document.getElementById('seo-preview-title');
        if (seoPreviewTitle) seoPreviewTitle.textContent = seoTitleVal || 'Tiêu đề sản phẩm';

        const seoDescEl = document.getElementById('seo-desc');
        if (seoDescEl) seoDescEl.value = seoDescVal;
        const seoDescCount = document.getElementById('seo-desc-count');
        if (seoDescCount) seoDescCount.textContent = `${seoDescVal.length} / 160 ký tự`;
        const seoPreviewDesc = document.getElementById('seo-preview-desc');
        if (seoPreviewDesc) seoPreviewDesc.textContent = seoDescVal || 'Mô tả sản phẩm sẽ hiển thị tại đây...';

        // 8. Tác giả thiết kế (Author) — khớp theo ID, hoặc theo tên, hoặc fallback tác giả đầu tiên của Store hiện tại
        const rawAuthorId = String(payload.authorId || '').trim();
        const rawAuthorName = String(payload.authorName || '').trim();
        state.pendingAuthorName = rawAuthorName;

        let matchedAuthor = null;
        if (Array.isArray(state.authors) && state.authors.length > 0) {
            if (rawAuthorId) {
                const idTail = rawAuthorId.split('/').pop();
                matchedAuthor = state.authors.find(a => a.id === rawAuthorId || (idTail && a.id && a.id.endsWith('/' + idTail)));
            }
            if (!matchedAuthor && rawAuthorName) {
                const cleanName = rawAuthorName.toLowerCase();
                matchedAuthor = state.authors.find(a => String(a.name || a.displayName || '').trim().toLowerCase() === cleanName);
            }
            if (!matchedAuthor && (rawAuthorId || rawAuthorName)) {
                matchedAuthor = state.authors[0];
            }
        }
        if (matchedAuthor && typeof selectInlineAuthor === 'function') {
            selectInlineAuthor(matchedAuthor.id);
        } else {
            state.selectedAuthorId = rawAuthorId;
            const authorHidden = document.getElementById('selected-author-id');
            if (authorHidden) authorHidden.value = rawAuthorId;
        }

        // 9. Mô tả mở rộng (Rich Description) & Nội dung tìm kiếm AI (AEO)
        const richDescEl = document.getElementById('rich-description');
        if (richDescEl) richDescEl.value = payload.richDescription || '';

        const aeoEl = document.getElementById('aeo-html');
        if (aeoEl) aeoEl.value = payload.aeoHtml || '';

        // 10. Phong cách nội thất (Interior Style) & Không gian phòng (Room Type)
        const styles = new Set((payload.interiorStyle || []).map(s => String(s).trim().toLowerCase()));
        document.querySelectorAll('input[name="interior_style"]').forEach(cb => {
            cb.checked = styles.has(cb.value.trim().toLowerCase());
        });
        const rooms = new Set((payload.roomType || []).map(r => String(r).trim().toLowerCase()));
        document.querySelectorAll('input[name="room_type"]').forEach(cb => {
            cb.checked = rooms.has(cb.value.trim().toLowerCase());
        });

        // 11. Tùy chọn & Ma trận biến thể (hỗ trợ đầy đủ Sparse Variants)
        const rawOpts = Array.isArray(payload.options) ? payload.options : [];
        const rawVars = Array.isArray(payload.variants) ? payload.variants : [];
        if (rawOpts.length > 0) {
            state.options = rawOpts.map(opt => ({
                clientId: 'opt_' + Math.random().toString(36).substr(2, 9),
                name: String(opt.name || 'Option').trim() || 'Option',
                isEditing: false,
                values: (opt.values || []).map(v => ({
                    clientId: 'val_' + Math.random().toString(36).substr(2, 9),
                    label: String(typeof v === 'object' ? (v.label || v.name || v.value || '') : v).trim()
                })).filter(vo => vo.label.length > 0)
            })).filter(o => o.values.length > 0);

            if (state.options.length > 0) {
                state.variantsByKey = {};
                const cartesian = state.options.reduce((acc, opt) => {
                    const next = [];
                    acc.forEach(prefix => {
                        opt.values.forEach(valObj => {
                            next.push([...prefix, { optName: opt.name, clientId: valObj.clientId, label: valObj.label }]);
                        });
                    });
                    return next;
                }, [[]]);

                cartesian.forEach(comb => {
                    const key = comb.map(c => c.clientId).join('_');
                    state.variantsByKey[key] = {
                        enabled: false,
                        price: '',
                        compareAtPrice: '',
                        sku: '',
                        barcode: ''
                    };
                });

                rawVars.forEach(v => {
                    const optVals = Array.isArray(v.optionValues) ? v.optionValues : [];
                    const matchedIds = state.options.map((opt, idx) => {
                        const foundOv = optVals.find(ov => String(ov.optionName || '').trim().toLowerCase() === opt.name.toLowerCase()) || optVals[idx];
                        const targetLabel = foundOv ? String(foundOv.name ?? foundOv.value ?? '').trim().toLowerCase() : '';
                        const matchedVal = opt.values.find(vo => vo.label.toLowerCase() === targetLabel) || opt.values[0];
                        return matchedVal ? matchedVal.clientId : null;
                    });
                    if (matchedIds.every(Boolean)) {
                        const key = matchedIds.join('_');
                        state.variantsByKey[key] = {
                            enabled: true,
                            price: String(v.price ?? ''),
                            compareAtPrice: String(v.compareAtPrice ?? ''),
                            sku: String(v.sku ?? ''),
                            barcode: String(v.barcode ?? '')
                        };
                    }
                });

                state.showDisabledVariants = false;
                renderOptions();
                rebuildVariantMatrix();
            }
        } else if (rawVars.length > 0) {
            const firstVar = rawVars[0] || {};
            const optClientId = 'opt_' + Math.random().toString(36).substr(2, 9);
            const valClientId = 'val_' + Math.random().toString(36).substr(2, 9);
            state.options = [{
                clientId: optClientId,
                name: 'Style',
                isEditing: false,
                values: [{ clientId: valClientId, label: 'Default' }]
            }];
            state.variantsByKey = {
                [valClientId]: {
                    enabled: true,
                    price: String(firstVar.price ?? ''),
                    compareAtPrice: String(firstVar.compareAtPrice ?? ''),
                    sku: String(firstVar.sku ?? ''),
                    barcode: String(firstVar.barcode ?? '')
                }
            };
            state.showDisabledVariants = false;
            renderOptions();
            rebuildVariantMatrix();
        }
    } finally {
        isBatchUpdating = false;
        updateValidationState();
        if (typeof updateSubmitButtonLabel === 'function') {
            updateSubmitButtonLabel();
        }
    }
}

/**
 * Nạp một sản phẩm bị lỗi trong bảng kết quả lên biểu mẫu bên dưới để chỉnh sửa trực tiếp
 */
async function loadFailedBulkItemToForm(itemIndex) {
    if (!state.currentBulkJobSnapshot) return;
    const jobId = state.currentBulkJobSnapshot.job_id;

    // Nếu sản phẩm vẫn nằm trong selectedBulkProducts hiện tại và có dữ liệu CSV gốc
    if (Array.isArray(state.selectedBulkProducts) && state.selectedBulkProducts[itemIndex]) {
        const selItem = state.selectedBulkProducts[itemIndex];
        state.activeBulkProductId = selItem.clientId;
        if (selItem.payload) {
            populateFormFromPayloadObject(selItem.payload);
        } else if (selItem.handle) {
            await populateProductFromCsv(selItem.handle);
        }
        const formCard = document.getElementById('product-handle') || document.getElementById('product-title');
        if (formCard) formCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        showToast(`Đã nạp "${selItem.title || selItem.handle}" lên biểu mẫu để chỉnh sửa.`, true);
        return;
    }

    // Trường hợp tải lại trang (chưa có payload trong bộ nhớ): lấy payload từ SQLite của Job
    const fullJob = await syncBulkJobSnapshotFromServer(jobId, true);
    if (!fullJob || !Array.isArray(fullJob.items)) return;
    const target = fullJob.items.find(it => it.item_index === itemIndex) || fullJob.items[itemIndex];
    if (!target || !target.payload) {
        showToast('Không tìm thấy dữ liệu gốc của sản phẩm này.', false);
        return;
    }

    // Chuyển sang chế độ chỉnh sửa 1 sản phẩm hoặc nạp vào danh sách chờ nếu đang trống
    state.selectedBulkProducts = [{
        clientId: `retry_${itemIndex}_${Date.now()}`,
        handle: target.handle,
        title: target.title,
        descriptionHtml: target.payload.descriptionHtml || '',
        payload: target.payload,
        status: 'PENDING',
        error: null,
        links: null
    }];
    state.activeBulkProductId = state.selectedBulkProducts[0].clientId;
    updateFloatingBulkBadge();
    populateFormFromPayloadObject(target.payload);

    const handleInput = document.getElementById('product-handle') || document.getElementById('product-title');
    if (handleInput) {
        handleInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
        handleInput.focus();
    }
    showToast(`Đã nạp "${target.title || target.handle}" vào biểu mẫu — bạn có thể sửa Handle và bấm tạo lại ngay!`, true);
}

/**
 * Lọc giữ lại duy nhất các sản phẩm bị lỗi trong lần chạy vừa rồi để người dùng chỉnh sửa & tạo lại
 * mà không tạo trùng lại các sản phẩm đã thành công.
 */
async function keepOnlyFailedBulkItemsForRetry() {
    if (!state.currentBulkJobSnapshot) return;
    const jobId = state.currentBulkJobSnapshot.job_id;
    const fullJob = await syncBulkJobSnapshotFromServer(jobId, true);
    if (!fullJob || !Array.isArray(fullJob.items)) return;

    const failedItems = fullJob.items.filter(it => isBulkStatusFailed(it.status) && it.payload);
    if (failedItems.length === 0) {
        showToast('Không có sản phẩm lỗi nào cần tạo lại.', true);
        return;
    }

    state.selectedBulkProducts = failedItems.map((it, idx) => ({
        clientId: `retry_bulk_${idx}_${Date.now()}`,
        handle: it.handle,
        title: it.title,
        descriptionHtml: it.payload.descriptionHtml || '',
        payload: it.payload,
        status: 'PENDING',
        error: null,
        links: null
    }));
    state.activeBulkProductId = state.selectedBulkProducts[0].clientId;
    updateFloatingBulkBadge();
    populateFormFromPayloadObject(state.selectedBulkProducts[0].payload);

    showToast(`Đã lọc giữ lại ${failedItems.length} sản phẩm bị lỗi vào danh sách chờ và mở sản phẩm lỗi đầu tiên trên form!`, true);
    const handleInput = document.getElementById('product-handle') || document.getElementById('product-title');
    if (handleInput) {
        handleInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// =============================================================================
// BẢN LƯU TRỮ TẠO GẦN NHẤT (LATEST SERVER-SIDE JSON ARCHIVE MODAL)
// =============================================================================

let _isLatestArchiveBackdropMousedown = false;
let _latestArchiveJsonTextCache = '';

function handleLatestArchiveBackdropMouseDown(e) {
    _isLatestArchiveBackdropMousedown = (e.target === e.currentTarget);
}

function handleLatestArchiveBackdropClick(e) {
    if (_isLatestArchiveBackdropMousedown && e.target === e.currentTarget) {
        closeLatestArchiveModal();
    }
    _isLatestArchiveBackdropMousedown = false;
}

function closeLatestArchiveModal() {
    const modal = document.getElementById('latestArchiveModal');
    if (modal) modal.classList.add('hidden');
}

function formatArchiveTimestampVi(isoStr) {
    if (!isoStr) return '—';
    try {
        const d = new Date(isoStr);
        if (isNaN(d.getTime())) return isoStr;
        return d.toLocaleString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    } catch (e) {
        return isoStr;
    }
}

function isArchiveStatusFailed(status) {
    const st = String(status || '').trim().toUpperCase();
    return st === 'FAILED' || st === 'FAILED_VALIDATION' || st === 'ERROR';
}

/**
 * Cập nhật huy hiệu số lượng sản phẩm trên nút "Bản lưu trữ tạo gần nhất" ở Header
 */
async function refreshLatestArchiveSummary() {
    const pill = document.getElementById('latest-archive-count-pill');
    try {
        const resp = await fetch('/api/products/latest-archive?include_payload=false');
        if (!resp.ok) return;
        const data = await resp.json();
        const archive = data && data.archive ? data.archive : null;
        if (pill) {
            if (archive && Number(archive.total_items) > 0) {
                pill.textContent = `${archive.total_items} SP`;
                pill.classList.remove('hidden');
            } else {
                pill.classList.add('hidden');
            }
        }
        // Nếu popup Bản lưu trữ đang mở thì đồng bộ lại dữ liệu đầy đủ
        const modal = document.getElementById('latestArchiveModal');
        if (modal && !modal.classList.contains('hidden')) {
            await loadLatestArchiveFullData();
        }
    } catch (e) {
        console.warn('refreshLatestArchiveSummary warning:', e);
    }
}

async function loadLatestArchiveFullData() {
    const loadingEl = document.getElementById('latest-archive-loading');
    const emptyEl = document.getElementById('latest-archive-empty');
    const tableWrap = document.getElementById('latest-archive-table-container');

    if (loadingEl) loadingEl.classList.remove('hidden');
    if (emptyEl) emptyEl.classList.add('hidden');
    if (tableWrap) tableWrap.classList.add('hidden');

    try {
        const resp = await fetch('/api/products/latest-archive?include_payload=true');
        const data = await resp.json();
        state.latestArchiveData = (data && data.archive) ? data.archive : null;

        const pill = document.getElementById('latest-archive-count-pill');
        if (pill) {
            if (state.latestArchiveData && Number(state.latestArchiveData.total_items) > 0) {
                pill.textContent = `${state.latestArchiveData.total_items} SP`;
                pill.classList.remove('hidden');
            } else {
                pill.classList.add('hidden');
            }
        }
    } catch (err) {
        console.error('Lỗi tải Bản lưu trữ tạo gần nhất:', err);
        state.latestArchiveData = null;
        showToast('Không thể tải Bản lưu trữ tạo gần nhất: ' + err.message, false);
    } finally {
        if (loadingEl) loadingEl.classList.add('hidden');
    }

    renderLatestArchiveModalView();
}

async function openLatestArchiveModal() {
    const modal = document.getElementById('latestArchiveModal');
    if (!modal) return;

    state.latestArchiveFilter = 'all';
    state.latestArchiveSearchQuery = '';
    const searchInput = document.getElementById('latest-archive-search-input');
    if (searchInput) searchInput.value = '';
    closeLatestArchiveJsonViewer();

    modal.classList.remove('hidden');
    await loadLatestArchiveFullData();
}

function handleLatestArchiveSearch(val) {
    state.latestArchiveSearchQuery = String(val || '').trim();
    renderLatestArchiveModalView();
}

function setLatestArchiveFilter(filter) {
    state.latestArchiveFilter = filter || 'all';
    renderLatestArchiveModalView();
}

function resolveArchiveStoreDomain(archive) {
    if (!archive) return '';
    const explicit = String(archive.store_domain || (archive.metadata && archive.metadata.store_domain) || '').trim();
    if (explicit) {
        const cleaned = explicit.replace(/^https?:\/\//i, '').split('/')[0].split(':')[0].toLowerCase();
        if (cleaned) {
            return cleaned.includes('.') ? cleaned : `${cleaned}.myshopify.com`;
        }
    }
    const isCustom = String(archive.store_type || '').toLowerCase() === 'custom';
    const items = Array.isArray(archive.items) ? archive.items : [];
    for (const it of items) {
        const sf = it && it.links && (it.links.storefront || it.links.storefront_url);
        if (sf && sf.includes('.myshopify.com')) {
            const m = sf.match(/https?:\/\/([^/]+\.myshopify\.com)/i);
            if (m && m[1]) return m[1].toLowerCase();
        }
        const adm = it && it.links && (it.links.shopify_admin || it.links.shopify_admin_url);
        if (adm && adm.includes('admin.shopify.com/store/')) {
            const m = adm.match(/admin\.shopify\.com\/store\/([^/?#]+)/i);
            if (m && m[1]) return `${m[1].toLowerCase()}.myshopify.com`;
        }
    }
    if (
        typeof CURRENT_STORE_DOMAIN === 'string' &&
        CURRENT_STORE_DOMAIN.trim() &&
        ((isCustom && CURRENT_STORE_TYPE === 'custom') || (!isCustom && CURRENT_STORE_TYPE !== 'custom'))
    ) {
        return CURRENT_STORE_DOMAIN.trim();
    }
    return isCustom ? '236qm8-w7.myshopify.com' : 'wrydeco.myshopify.com';
}

function formatArchiveStoreBadgeLabel(archive) {
    const isCustom = String((archive && archive.store_type) || '').toLowerCase() === 'custom';
    const typeLabel = isCustom ? 'Store Riêng' : 'Store Mặc định';
    const domain = resolveArchiveStoreDomain(archive);
    return domain ? `${typeLabel}: ${domain}` : typeLabel;
}

function renderLatestArchiveModalView() {
    const archive = state.latestArchiveData;
    const modeBadge = document.getElementById('latest-archive-mode-badge');
    const storeBadge = document.getElementById('latest-archive-store-badge');
    const statusBadge = document.getElementById('latest-archive-status-badge');
    const subtitleEl = document.getElementById('latest-archive-meta-subtitle');
    const toolbarEl = document.getElementById('latest-archive-toolbar');
    const emptyEl = document.getElementById('latest-archive-empty');
    const tableWrap = document.getElementById('latest-archive-table-container');
    const tbody = document.getElementById('latest-archive-table-body');
    const reuseFailedBtn = document.getElementById('btn-archive-reuse-failed');
    const reuseFailedLabel = document.getElementById('btn-archive-reuse-failed-label');
    const reuseAllBtn = document.getElementById('btn-archive-reuse-all');
    const reuseAllLabel = document.getElementById('btn-archive-reuse-all-label');

    if (!archive || !Array.isArray(archive.items) || archive.items.length === 0) {
        if (modeBadge) modeBadge.textContent = 'Chưa có dữ liệu';
        if (storeBadge) storeBadge.textContent = '—';
        if (statusBadge) {
            statusBadge.textContent = 'Trống';
            statusBadge.className = 'px-2.5 py-0.5 rounded-full text-sm font-bold bg-gray-100 text-gray-600 border border-gray-200';
        }
        if (subtitleEl) {
            subtitleEl.textContent = 'Lưu trữ JSON tự động trên máy chủ cho lần tạo sản phẩm gần nhất (dù thành công hay thất bại).';
        }
        if (toolbarEl) toolbarEl.classList.add('hidden');
        if (emptyEl) emptyEl.classList.remove('hidden');
        if (tableWrap) tableWrap.classList.add('hidden');
        if (reuseFailedBtn) reuseFailedBtn.classList.add('hidden');
        if (reuseAllBtn) reuseAllBtn.classList.add('hidden');
        return;
    }

    if (toolbarEl) toolbarEl.classList.remove('hidden');
    if (emptyEl) emptyEl.classList.remove('block');
    if (emptyEl) emptyEl.classList.add('hidden');
    if (tableWrap) tableWrap.classList.remove('hidden');

    const items = archive.items || [];
    const total = items.length;
    const successItems = items.filter(it => String(it.status || '').toUpperCase() === 'SUCCESS');
    const failedItems = items.filter(it => isArchiveStatusFailed(it.status));

    if (modeBadge) {
        const isBulk = String(archive.mode || '').toLowerCase() === 'bulk';
        modeBadge.textContent = isBulk ? `Tạo hàng loạt (${total} SP)` : 'Tạo đơn lẻ (1 SP)';
        modeBadge.className = isBulk
            ? 'px-2.5 py-0.5 rounded-full text-sm font-bold bg-indigo-50 text-indigo-800 border border-indigo-200'
            : 'px-2.5 py-0.5 rounded-full text-sm font-bold bg-purple-50 text-purple-800 border border-purple-200';
    }

    if (storeBadge) {
        const isCustom = String(archive.store_type || '').toLowerCase() === 'custom';
        storeBadge.textContent = formatArchiveStoreBadgeLabel(archive);
        storeBadge.className = isCustom
            ? 'px-2.5 py-0.5 rounded-full text-sm font-bold bg-teal-50 text-teal-800 border border-teal-200'
            : 'px-2.5 py-0.5 rounded-full text-sm font-bold bg-gray-100 text-gray-700 border border-gray-200';
    }

    if (statusBadge) {
        const overall = String(archive.overall_status || '').toUpperCase();
        if (overall === 'RUNNING' || overall === 'READY') {
            statusBadge.textContent = `Đang xử lý (${successItems.length + failedItems.length}/${total})`;
            statusBadge.className = 'px-2.5 py-0.5 rounded-full text-sm font-bold bg-indigo-100 text-indigo-800 border border-indigo-200';
        } else if (failedItems.length === 0 && successItems.length > 0) {
            statusBadge.textContent = `Thành công (${successItems.length}/${total})`;
            statusBadge.className = 'px-2.5 py-0.5 rounded-full text-sm font-bold bg-emerald-50 text-emerald-800 border border-emerald-200';
        } else if (successItems.length === 0 && failedItems.length > 0) {
            statusBadge.textContent = `Thất bại (${failedItems.length}/${total} lỗi)`;
            statusBadge.className = 'px-2.5 py-0.5 rounded-full text-sm font-bold bg-red-50 text-red-800 border border-red-200';
        } else {
            statusBadge.textContent = `${successItems.length} thành công • ${failedItems.length} thất bại`;
            statusBadge.className = 'px-2.5 py-0.5 rounded-full text-sm font-bold bg-amber-50 text-amber-900 border border-amber-200';
        }
    }

    if (subtitleEl) {
        const timeText = formatArchiveTimestampVi(archive.updated_at || archive.saved_at);
        const jobPart = archive.job_id ? ` • Job: ${archive.job_id}` : '';
        subtitleEl.textContent = `File JSON máy chủ: latest_create_archive.json • Lưu lúc: ${timeText}${jobPart}`;
    }

    // Cập nhật bộ đếm và trạng thái active trên 3 nút lọc
    const countAllEl = document.getElementById('archive-filter-count-all');
    const countFailedEl = document.getElementById('archive-filter-count-failed');
    const countSuccessEl = document.getElementById('archive-filter-count-success');
    if (countAllEl) countAllEl.textContent = String(total);
    if (countFailedEl) countFailedEl.textContent = String(failedItems.length);
    if (countSuccessEl) countSuccessEl.textContent = String(successItems.length);

    const activeFilter = state.latestArchiveFilter || 'all';
    const btnAll = document.getElementById('archive-filter-btn-all');
    const btnFailed = document.getElementById('archive-filter-btn-failed');
    const btnSuccess = document.getElementById('archive-filter-btn-success');

    if (btnAll) {
        btnAll.className = activeFilter === 'all'
            ? 'px-3 py-1.5 rounded-xl text-sm font-bold bg-gray-900 text-white cursor-pointer transition-colors'
            : 'px-3 py-1.5 rounded-xl text-sm font-bold bg-white text-gray-700 hover:bg-gray-100 border border-gray-300 cursor-pointer transition-colors';
    }
    if (btnFailed) {
        btnFailed.className = activeFilter === 'failed'
            ? 'px-3 py-1.5 rounded-xl text-sm font-bold bg-red-600 text-white cursor-pointer transition-colors'
            : 'px-3 py-1.5 rounded-xl text-sm font-bold bg-red-50 text-red-700 hover:bg-red-100 border border-red-200 cursor-pointer transition-colors';
    }
    if (btnSuccess) {
        btnSuccess.className = activeFilter === 'success'
            ? 'px-3 py-1.5 rounded-xl text-sm font-bold bg-emerald-600 text-white cursor-pointer transition-colors'
            : 'px-3 py-1.5 rounded-xl text-sm font-bold bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 cursor-pointer transition-colors';
    }

    // Nút phụ ở Footer để nạp lại hàng loạt
    if (reuseFailedBtn && reuseFailedLabel) {
        if (failedItems.length > 0 && total > 1) {
            reuseFailedBtn.classList.remove('hidden');
            reuseFailedLabel.textContent = `Nạp ${failedItems.length} SP lỗi vào hàng loạt`;
        } else {
            reuseFailedBtn.classList.add('hidden');
        }
    }
    if (reuseAllBtn && reuseAllLabel) {
        if (total > 1) {
            reuseAllBtn.classList.remove('hidden');
            reuseAllLabel.textContent = `Nạp tất cả (${total} SP) vào hàng loạt`;
        } else {
            reuseAllBtn.classList.add('hidden');
        }
    }

    // Lọc danh sách theo từ khóa tìm kiếm và trạng thái
    const q = (state.latestArchiveSearchQuery || '').toLowerCase();
    const filtered = items
        .map((it, idx) => ({ item: it, index: typeof it.item_index === 'number' ? it.item_index : idx, arrayIndex: idx }))
        .filter(({ item }) => {
            const st = String(item.status || '').toUpperCase();
            if (activeFilter === 'failed' && !isArchiveStatusFailed(st)) return false;
            if (activeFilter === 'success' && st !== 'SUCCESS') return false;
            if (q) {
                const hay = `${item.title || ''} ${item.handle || ''} ${item.error_message || ''} ${(item.summary && item.summary.product_type) || ''}`.toLowerCase();
                if (!hay.includes(q)) return false;
            }
            return true;
        });

    if (!tbody) return;

    if (filtered.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="py-8 px-4 text-center text-gray-500 font-medium">
                    Không có sản phẩm nào khớp với bộ lọc hiện tại.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.map(({ item, index, arrayIndex }) => {
        const st = String(item.status || 'PENDING').toUpperCase();
        const summary = item.summary || {};
        const thumbUrl = summary.thumbnail_url || '';
        const varCount = summary.variant_count ?? ((item.payload && Array.isArray(item.payload.variants)) ? item.payload.variants.length : 0);
        const mediaCount = summary.media_count ?? ((item.payload && Array.isArray(item.payload.media)) ? item.payload.media.length : 0);
        const pricePreview = summary.price_preview || '';
        const prodType = summary.product_type || (item.payload && item.payload.productType) || '';

        let statusHtml = '';
        let detailHtml = '';

        if (st === 'SUCCESS') {
            statusHtml = `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-bold bg-emerald-50 text-emerald-700 border border-emerald-200"><iconify-icon icon="mdi:check-circle"></iconify-icon>Thành công</span>`;
            const pidNum = item.product_id ? String(item.product_id).split('/').pop() : '';
            const links = item.links || {};
            const adminLink = links.shopify_admin || links.shopify_admin_url || '';
            const toolLink = links.tool || links.tool_url || '';
            detailHtml = `
                <div class="text-sm text-emerald-800 font-medium mt-1">
                    ${pidNum ? `Shopify ID: <span class="font-mono">${escapeHtml(pidNum)}</span>` : 'Đã tạo thành công'}
                    ${adminLink ? ` • <a href="${escapeHtml(adminLink)}" target="_blank" rel="noopener noreferrer" class="underline hover:text-emerald-950 font-bold">Admin</a>` : ''}
                    ${toolLink ? ` • <a href="${escapeHtml(toolLink)}" target="_blank" rel="noopener noreferrer" class="underline hover:text-emerald-950 font-bold">Tool</a>` : ''}
                </div>
            `;
        } else if (isArchiveStatusFailed(st)) {
            statusHtml = `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-bold bg-red-50 text-red-700 border border-red-200"><iconify-icon icon="mdi:alert-circle"></iconify-icon>Thất bại</span>`;
            const errMsg = item.error_message || 'Lỗi không xác định khi tạo sản phẩm.';
            detailHtml = `<p class="text-sm text-red-700 mt-1 leading-snug line-clamp-2" title="${escapeHtml(errMsg)}">${escapeHtml(errMsg)}</p>`;
        } else {
            statusHtml = `<span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-sm font-bold bg-amber-50 text-amber-800 border border-amber-200"><iconify-icon icon="mdi:clock-outline"></iconify-icon>${escapeHtml(st)}</span>`;
            detailHtml = `<p class="text-sm text-gray-500 mt-1">Đang chờ hoặc đang xử lý trên máy chủ.</p>`;
        }

        const thumbHtml = thumbUrl
            ? `<img src="${escapeHtml(thumbUrl)}" alt="" class="w-11 h-11 rounded-lg object-cover border border-gray-200 shrink-0 bg-gray-50">`
            : `<div class="w-11 h-11 rounded-lg border border-gray-200 bg-gray-100 text-gray-400 flex items-center justify-center shrink-0"><iconify-icon icon="mdi:image-off-outline" class="text-lg"></iconify-icon></div>`;

        return `
            <tr class="hover:bg-indigo-50/30 transition-colors">
                <td class="py-3.5 px-2.5 text-center font-bold text-gray-500">${index + 1}</td>
                <td class="py-3.5 px-3.5 overflow-hidden">
                    <div class="flex items-center gap-3 min-w-0">
                        ${thumbHtml}
                        <div class="min-w-0 flex-1">
                            <p class="font-bold text-gray-900 leading-snug truncate" title="${escapeHtml(item.title || '(Chưa có tiêu đề)')}">${escapeHtml(item.title || '(Chưa có tiêu đề)')}</p>
                            <p class="text-sm font-mono text-gray-500 truncate mt-0.5" title="${escapeHtml(item.handle || '')}">${escapeHtml(item.handle || '—')}</p>
                        </div>
                    </div>
                </td>
                <td class="py-3.5 px-3.5 overflow-hidden">
                    <div class="flex flex-wrap items-center gap-1.5 text-sm font-semibold text-gray-700">
                        <span class="px-2 py-0.5 bg-gray-100 rounded-md border border-gray-200 whitespace-nowrap">${mediaCount} ảnh</span>
                        <span class="px-2 py-0.5 bg-gray-100 rounded-md border border-gray-200 whitespace-nowrap">${varCount} biến thể</span>
                        ${pricePreview ? `<span class="px-2 py-0.5 bg-indigo-50 text-indigo-800 rounded-md border border-indigo-100 whitespace-nowrap">${escapeHtml(pricePreview)}</span>` : ''}
                    </div>
                    ${prodType ? `<p class="text-sm text-gray-500 mt-1 truncate">Loại: ${escapeHtml(prodType)}</p>` : ''}
                </td>
                <td class="py-3.5 px-3.5 overflow-hidden">
                    ${statusHtml}
                    ${detailHtml}
                </td>
                <td class="py-3.5 px-3.5 text-right">
                    <div class="inline-flex items-center justify-end gap-1.5 whitespace-nowrap">
                        <button type="button" onclick="inspectArchiveItemJson(${arrayIndex})" class="px-2.5 py-1.5 bg-white hover:bg-gray-100 text-gray-700 border border-gray-300 text-sm font-bold rounded-xl transition-colors cursor-pointer inline-flex items-center gap-1 shrink-0 whitespace-nowrap" title="Xem JSON chi tiết của sản phẩm này">
                            <iconify-icon icon="mdi:code-json" class="text-sm text-indigo-600 shrink-0"></iconify-icon>
                            <span>JSON</span>
                        </button>
                        <button type="button" onclick="selectProductFromLatestArchive(${arrayIndex})" class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded-xl shadow-2xs transition-colors cursor-pointer inline-flex items-center gap-1.5 shrink-0 whitespace-nowrap" title="Điền toàn bộ dữ liệu sản phẩm này lên trang Tạo sản phẩm mới để chỉnh sửa">
                            <iconify-icon icon="mdi:file-document-edit-outline" class="text-sm shrink-0"></iconify-icon>
                            <span>Chọn & Điền</span>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Chọn 1 sản phẩm từ Bản lưu trữ tạo gần nhất -> Điền toàn bộ các trường lên trang để chỉnh sửa
 */
function selectProductFromLatestArchive(arrayIndex) {
    const archive = state.latestArchiveData;
    if (!archive || !Array.isArray(archive.items) || !archive.items[arrayIndex]) {
        showToast('Không tìm thấy sản phẩm đã chọn trong bản lưu trữ.', false);
        return;
    }

    const item = archive.items[arrayIndex];
    if (!item.payload || typeof item.payload !== 'object') {
        showToast('Sản phẩm này không có dữ liệu payload hợp lệ để điền.', false);
        return;
    }

    // Chuyển biểu mẫu về chế độ chỉnh sửa trực tiếp 1 sản phẩm để người dùng sửa và bấm tạo lại ngay
    state.selectedBulkProducts = [];
    state.activeBulkProductId = null;
    updateFloatingBulkBadge();

    // Ẩn các khung thông báo kết quả cũ để tập trung vào biểu mẫu chỉnh sửa
    const successSec = document.getElementById('create-success-actions-section');
    if (successSec) successSec.classList.add('hidden');
    const errSec = document.getElementById('create-error-section');
    if (errSec) errSec.classList.add('hidden');

    populateFormFromPayloadObject(item.payload);
    closeLatestArchiveModal();

    window.scrollTo({ top: 0, behavior: 'smooth' });
    showToast(`Đã điền đầy đủ dữ liệu sản phẩm "${item.title || item.handle || '#' + (arrayIndex + 1)}" từ Bản lưu trữ tạo gần nhất lên trang!`, true);
}

/**
 * Xem toàn bộ JSON của Bản lưu trữ tạo gần nhất hoặc JSON của 1 sản phẩm cụ thể
 */
function toggleLatestArchiveJsonViewer() {
    const panel = document.getElementById('latest-archive-json-panel');
    const pre = document.getElementById('latest-archive-json-pre');
    const titleEl = document.getElementById('latest-archive-json-title');
    const labelEl = document.getElementById('btn-toggle-archive-json-label');
    if (!panel || !pre) return;

    const isHidden = panel.classList.contains('hidden');
    if (!isHidden && titleEl && titleEl.dataset.scope === 'full') {
        closeLatestArchiveJsonViewer();
        return;
    }

    const formatted = JSON.stringify(state.latestArchiveData || {}, null, 2);
    _latestArchiveJsonTextCache = formatted;
    pre.textContent = formatted;
    if (titleEl) {
        titleEl.textContent = 'Toàn bộ dữ liệu JSON của Bản lưu trữ tạo gần nhất (latest_create_archive.json)';
        titleEl.dataset.scope = 'full';
    }
    if (labelEl) labelEl.textContent = 'Ẩn dữ liệu JSON';
    panel.classList.remove('hidden');
}

function inspectArchiveItemJson(arrayIndex) {
    const archive = state.latestArchiveData;
    if (!archive || !Array.isArray(archive.items) || !archive.items[arrayIndex]) return;

    const item = archive.items[arrayIndex];
    const panel = document.getElementById('latest-archive-json-panel');
    const pre = document.getElementById('latest-archive-json-pre');
    const titleEl = document.getElementById('latest-archive-json-title');
    const labelEl = document.getElementById('btn-toggle-archive-json-label');
    if (!panel || !pre) return;

    const formatted = JSON.stringify(item, null, 2);
    _latestArchiveJsonTextCache = formatted;
    pre.textContent = formatted;
    if (titleEl) {
        titleEl.textContent = `JSON sản phẩm #${arrayIndex + 1}: ${item.title || item.handle || ''}`;
        titleEl.dataset.scope = 'item';
    }
    if (labelEl) labelEl.textContent = 'Xem toàn bộ JSON';
    panel.classList.remove('hidden');
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeLatestArchiveJsonViewer() {
    const panel = document.getElementById('latest-archive-json-panel');
    const labelEl = document.getElementById('btn-toggle-archive-json-label');
    if (panel) panel.classList.add('hidden');
    if (labelEl) labelEl.textContent = 'Xem dữ liệu JSON';
}

async function copyLatestArchiveJson() {
    const text = _latestArchiveJsonTextCache || JSON.stringify(state.latestArchiveData || {}, null, 2);
    try {
        await navigator.clipboard.writeText(text);
        showToast('Đã sao chép dữ liệu JSON vào bộ nhớ tạm!', true);
    } catch (e) {
        showToast('Không thể sao chép tự động, vui lòng bôi đen trong khung JSON.', false);
    }
}

/**
 * Nạp lại danh sách sản phẩm (tất cả hoặc chỉ các sản phẩm lỗi) từ Bản lưu trữ vào hàng đợi tạo hàng loạt
 */
function reuseLatestArchiveItems(mode) {
    const archive = state.latestArchiveData;
    if (!archive || !Array.isArray(archive.items)) return;

    const sourceItems = mode === 'failed'
        ? archive.items.filter(it => isArchiveStatusFailed(it.status) && it.payload)
        : archive.items.filter(it => it && it.payload);

    if (sourceItems.length === 0) {
        showToast('Không có sản phẩm phù hợp trong bản lưu trữ để nạp lại.', false);
        return;
    }

    state.selectedBulkProducts = sourceItems.map((it, idx) => ({
        clientId: `archive_bulk_${idx}_${Date.now()}`,
        handle: it.handle || (it.payload && it.payload.handle) || '',
        title: it.title || (it.payload && it.payload.title) || '',
        descriptionHtml: (it.payload && it.payload.descriptionHtml) || '',
        payload: JSON.parse(JSON.stringify(it.payload)),
        status: 'PENDING',
        error: null,
        links: null
    }));
    state.activeBulkProductId = state.selectedBulkProducts[0].clientId;
    updateFloatingBulkBadge();
    populateFormFromPayloadObject(state.selectedBulkProducts[0].payload);
    closeLatestArchiveModal();
    window.scrollTo({ top: 0, behavior: 'smooth' });

    showToast(
        mode === 'failed'
            ? `Đã nạp ${sourceItems.length} sản phẩm bị lỗi từ Bản lưu trữ vào danh sách chờ hàng loạt!`
            : `Đã nạp toàn bộ ${sourceItems.length} sản phẩm từ Bản lưu trữ vào danh sách chờ hàng loạt!`,
        true
    );
}

// Export các hàm Bulk Progress, Sparse Variants & Bản lưu trữ tạo gần nhất ra window để onclick HTML luôn gọi được an toàn
if (typeof window !== 'undefined') {
    Object.assign(window, {
        reopenBulkProgressModal,
        closeBulkProgressModal,
        handleBulkProgressBackdropMouseDown,
        handleBulkProgressBackdropClick,
        loadFailedBulkItemToForm,
        keepOnlyFailedBulkItemsForRetry,
        openLatestArchiveModal,
        closeLatestArchiveModal,
        handleLatestArchiveBackdropMouseDown,
        handleLatestArchiveBackdropClick,
        handleLatestArchiveSearch,
        setLatestArchiveFilter,
        selectProductFromLatestArchive,
        toggleLatestArchiveJsonViewer,
        inspectArchiveItemJson,
        closeLatestArchiveJsonViewer,
        copyLatestArchiveJson,
        reuseLatestArchiveItems,
        refreshLatestArchiveSummary
    });
}
