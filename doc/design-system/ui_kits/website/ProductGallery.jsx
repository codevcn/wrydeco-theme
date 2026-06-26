/**
 * Product Gallery Grid
 */
export function ProductGallery() {
  const products = [
    { id: 1, name: 'Walnut Shelf', price: '$1,200', image: '🪑' },
    { id: 2, name: 'Oak Bench', price: '$1,800', image: '🛋️' },
    { id: 3, name: 'Maple Cabinet', price: '$2,400', image: '📦' },
    { id: 4, name: 'Cherry Table', price: '$2,800', image: '📋' },
  ];

  return (
    <section style={{
      padding: 'var(--sp-8) var(--layout-padding-desktop)',
      backgroundColor: 'white',
    }}>
      <h2 style={{
        fontSize: 'var(--font-size-display-md)',
        marginBottom: 'var(--sp-6)',
        color: 'var(--text-primary)',
      }}>
        Featured Collection
      </h2>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: 'var(--sp-5)',
      }}>
        {products.map((product) => (
          <div
            key={product.id}
            style={{
              backgroundColor: 'var(--color-cream)',
              borderRadius: 'var(--radius-sm)',
              overflow: 'hidden',
              boxShadow: 'var(--shadow-elevation-1)',
              cursor: 'pointer',
              transition: 'all var(--duration-short) var(--ease-standard)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = 'var(--shadow-elevation-2)';
              e.currentTarget.style.transform = 'translateY(-2px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = 'var(--shadow-elevation-1)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <div style={{
              fontSize: '64px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '200px',
              backgroundColor: 'var(--bg-secondary)',
            }}>
              {product.image}
            </div>
            <div style={{ padding: 'var(--sp-5)' }}>
              <h3 style={{
                fontSize: 'var(--font-size-body-lg)',
                marginBottom: 'var(--sp-2)',
                color: 'var(--text-primary)',
              }}>
                {product.name}
              </h3>
              <p style={{
                fontSize: 'var(--font-size-body-md)',
                color: 'var(--text-secondary)',
                marginBottom: 'var(--sp-3)',
              }}>
                {product.price}
              </p>
              <button style={{
                width: '100%',
                padding: '12px 16px',
                border: '1px solid var(--color-linen)',
                backgroundColor: 'transparent',
                color: 'var(--text-primary)',
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '600',
                transition: 'all var(--duration-short) var(--ease-standard)',
              }}
              onMouseEnter={(e) => {
                e.target.style.borderColor = 'var(--color-bark)';
                e.target.style.color = 'var(--color-bark)';
              }}
              onMouseLeave={(e) => {
                e.target.style.borderColor = 'var(--color-linen)';
                e.target.style.color = 'var(--text-primary)';
              }}>
                View Details
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
