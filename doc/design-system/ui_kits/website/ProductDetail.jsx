/**
 * Product Detail View
 */
export function ProductDetail() {
  const [quantity, setQuantity] = React.useState(1);
  const [showConsultation, setShowConsultation] = React.useState(false);

  return (
    <section style={{
      padding: 'var(--sp-8) var(--layout-padding-desktop)',
      backgroundColor: 'white',
    }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 'var(--sp-6)',
        maxWidth: '1200px',
      }}>
        {/* Product Image */}
        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-sm)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '400px',
          fontSize: '120px',
        }}>
          🪑
        </div>

        {/* Product Info */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-5)' }}>
          <div>
            <h1 style={{
              fontSize: 'var(--font-size-display-md)',
              marginBottom: 'var(--sp-2)',
              color: 'var(--text-primary)',
            }}>
              Walnut Shelving Unit
            </h1>
            <p style={{
              fontSize: 'var(--font-size-body-lg)',
              color: 'var(--text-secondary)',
              marginBottom: 'var(--sp-3)',
            }}>
              Premium handcrafted solid walnut with custom finishing
            </p>
            <div style={{
              fontSize: 'var(--font-size-display-sm)',
              color: 'var(--color-clay)',
              fontWeight: '700',
              marginBottom: 'var(--sp-4)',
            }}>
              $1,200
            </div>
          </div>

          {/* Specifications */}
          <div style={{
            borderTop: '1px solid var(--border-light)',
            borderBottom: '1px solid var(--border-light)',
            padding: 'var(--sp-4) 0',
          }}>
            <p style={{ fontSize: '12px', color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: 'var(--sp-2)', fontWeight: '600' }}>
              Specifications
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--sp-3)', fontSize: 'var(--font-size-body-sm)' }}>
              <div><strong>Dimensions:</strong> 48" W × 72" H × 12" D</div>
              <div><strong>Material:</strong> Solid Walnut</div>
              <div><strong>Finish:</strong> Natural Oil</div>
              <div><strong>Weight:</strong> 85 lbs</div>
            </div>
          </div>

          {/* Quantity & Actions */}
          <div style={{ display: 'flex', gap: 'var(--sp-4)', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--sp-2)' }}>
              <label style={{ fontSize: '14px', fontWeight: '600' }}>Qty:</label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                style={{
                  width: '60px',
                  padding: '8px 12px',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '14px',
                }}
              />
            </div>
            <button style={{
              flex: 1,
              padding: '14px 24px',
              backgroundColor: 'var(--color-ebony)',
              color: 'white',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              fontSize: '14px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all var(--duration-short) var(--ease-standard)',
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = 'var(--color-bark)';
              e.target.style.boxShadow = 'var(--shadow-elevation-2)';
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = 'var(--color-ebony)';
              e.target.style.boxShadow = 'none';
            }}>
              Add to Cart
            </button>
          </div>

          {/* Consultation CTA */}
          <button
            onClick={() => setShowConsultation(!showConsultation)}
            style={{
              padding: '12px 20px',
              backgroundColor: 'transparent',
              color: 'var(--color-ebony)',
              border: '1px solid var(--color-linen)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '14px',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all var(--duration-short) var(--ease-standard)',
            }}
            onMouseEnter={(e) => {
              e.target.style.borderColor = 'var(--color-bark)';
              e.target.style.color = 'var(--color-bark)';
            }}
            onMouseLeave={(e) => {
              e.target.style.borderColor = 'var(--color-linen)';
              e.target.style.color = 'var(--color-ebony)';
            }}
          >
            Schedule Private Consultation
          </button>

          {/* Consultation Form (conditional) */}
          {showConsultation && (
            <div style={{
              backgroundColor: 'var(--bg-primary)',
              padding: 'var(--sp-5)',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border-light)',
            }}>
              <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: 'var(--sp-3)' }}>Request Consultation</h4>
              <input type="email" placeholder="Email" style={{ width: '100%', padding: '10px 12px', marginBottom: 'var(--sp-2)', border: '1px solid var(--border-default)', borderRadius: 'var(--radius-sm)', fontSize: '14px' }} />
              <button style={{
                width: '100%',
                padding: '10px',
                backgroundColor: 'var(--color-sage)',
                color: 'white',
                border: 'none',
                borderRadius: 'var(--radius-sm)',
                fontSize: '14px',
                fontWeight: '600',
                cursor: 'pointer',
              }}>Submit</button>
            </div>
          )}

          {/* Sustainability Info */}
          <div style={{
            backgroundColor: 'var(--bg-primary)',
            padding: 'var(--sp-4)',
            borderRadius: 'var(--radius-sm)',
            fontSize: 'var(--font-size-body-sm)',
            color: 'var(--text-secondary)',
          }}>
            <p style={{ margin: 0, fontWeight: '600', marginBottom: 'var(--sp-2)' }}>♻ Sustainably Sourced</p>
            <p style={{ margin: 0 }}>Crafted from responsibly harvested walnut. Each piece supports sustainable forestry practices.</p>
          </div>
        </div>
      </div>
    </section>
  );
}
