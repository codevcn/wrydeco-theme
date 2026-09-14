/**
 * WRYDECO Centralized External API Service
 *
 * Provides unified, scalable endpoints and methods for all external API calls
 * outside standard Shopify routes (e.g. image upload, custom size requests, consultations).
 */
(function () {
  const BASE_URL = 'https://admin.wrydeco.com';

  const ENDPOINTS = {
    UPLOAD_IMAGE: `${BASE_URL}/api/upload-image`,
    CUSTOM_SIZE_REQUEST: `${BASE_URL}/api/custom-size-requests`,
    CONSULTATIONS: `${BASE_URL}/api/consultations`,
  };

  const WrydecoApi = {
    BASE_URL,
    ENDPOINTS,

    /**
     * Upload an image file for custom color / finish.
     * @param {File} file
     * @returns {Promise<{ ok: boolean, status: number, data: { image_url?: string, [key: string]: any } }>}
     */
    async uploadCustomColorImage(file) {
      if (!file) {
        throw new Error('No file provided for upload.');
      }

      const formData = new FormData();
      formData.append('image', file);

      // Never set Content-Type header manually; let the browser inject multipart boundary.
      const response = await fetch(this.ENDPOINTS.UPLOAD_IMAGE, {
        method: 'POST',
        body: formData,
      });

      let data = {};
      try {
        data = await response.json();
      } catch (parseError) {
        data = {};
      }

      return {
        ok: response.ok,
        status: response.status,
        data,
      };
    },

    /**
     * Submit a quick custom size request.
     * @param {FormData|Object} payload
     * @returns {Promise<{ ok: boolean, status: number, data: any }>}
     */
    async submitCustomSizeRequest(payload) {
      let body;
      if (payload instanceof FormData) {
        body = payload;
      } else {
        body = new FormData();
        Object.entries(payload || {}).forEach(([key, value]) => {
          if (value != null) body.append(key, value);
        });
      }

      const response = await fetch(this.ENDPOINTS.CUSTOM_SIZE_REQUEST, {
        method: 'POST',
        body,
      });

      let data = {};
      try {
        data = await response.json();
      } catch (parseError) {
        data = {};
      }

      return {
        ok: response.ok,
        status: response.status,
        data,
      };
    },

    /**
     * Submit a bespoke consultation request form.
     * @param {FormData} formData
     * @param {string} [customEndpoint]
     * @returns {Promise<{ ok: boolean, status: number, data: any }>}
     */
    async submitConsultation(formData, customEndpoint) {
      const endpoint = customEndpoint || this.ENDPOINTS.CONSULTATIONS;

      const response = await fetch(endpoint, {
        method: 'POST',
        body: formData,
      });

      let data = null;
      try {
        data = await response.json();
      } catch (parseError) {
        data = null;
      }

      return {
        ok: response.ok,
        status: response.status,
        data,
      };
    },
  };

  window.WrydecoApi = WrydecoApi;
})();
