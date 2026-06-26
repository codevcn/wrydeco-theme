/**
 * Homepage Hero Section
 */
export function Hero({ onExplore = () => {} }) {
  return (
    <section style={{
      paddingTop: 'var(--sp-8)',
      paddingBottom: 'var(--sp-8)',
      paddingLeft: 'var(--layout-padding-desktop)',
      paddingRight: 'var(--layout-padding-desktop)',
      textAlign: 'center',
      backgroundColor: 'var(--bg-primary)',
      borderBottom: '1px solid var(--border-light)',
    }}>
      <h1 style={{
        fontSize: 'var(--font-size-display-lg)',
        marginBottom: 'var(--sp-4)',
        color: 'var(--text-primary)',
      }}>
        Handcrafted Elegance
      </h1>
      <p style={{
        fontSize: 'var(--font-size-body-lg)',
        color: 'var(--text-secondary)',
        maxWidth: '600px',
        marginLeft: 'auto',
        marginRight: 'auto',
        marginBottom: 'var(--sp-6)',
        lineHeight: 'var(--line-height-generous)',
      }}>
        Discover our curated collection of premium artisan furniture and home décor. Each piece is handcrafted with care and made from sustainably sourced materials.
      </p>
      <button
        onClick={onExplore}
        style={{
          padding: '16px 28px',
          fontSize: '16px',
          fontWeight: '600',
          border: 'none',
          borderRadius: 'var(--radius-sm)',
          backgroundColor: 'var(--color-ebony)',
          color: 'white',
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
        }}
      >
        Explore Collection
      </button>
    </section>
  );
}
