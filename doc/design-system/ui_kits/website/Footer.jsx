/**
 * Footer Section
 */
export function Footer() {
  return (
    <footer style={{
      backgroundColor: 'var(--color-ebony)',
      color: 'white',
      padding: 'var(--sp-8) var(--layout-padding-desktop)',
      borderTop: '1px solid var(--border-dark)',
    }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: 'var(--sp-6)',
        marginBottom: 'var(--sp-8)',
        maxWidth: '1200px',
      }}>
        <div>
          <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: 'var(--sp-3)' }}>Shop</h4>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li style={{ marginBottom: 'var(--sp-2)' }}><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>Furniture</a></li>
            <li style={{ marginBottom: 'var(--sp-2)' }}><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>Collections</a></li>
            <li><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>New Arrivals</a></li>
          </ul>
        </div>
        <div>
          <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: 'var(--sp-3)' }}>About</h4>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li style={{ marginBottom: 'var(--sp-2)' }}><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>Our Story</a></li>
            <li style={{ marginBottom: 'var(--sp-2)' }}><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>Sustainability</a></li>
            <li><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>Artisans</a></li>
          </ul>
        </div>
        <div>
          <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: 'var(--sp-3)' }}>Support</h4>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li style={{ marginBottom: 'var(--sp-2)' }}><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>Contact</a></li>
            <li style={{ marginBottom: 'var(--sp-2)' }}><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>Shipping</a></li>
            <li><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>Returns</a></li>
          </ul>
        </div>
        <div>
          <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: 'var(--sp-3)' }}>Connect</h4>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li style={{ marginBottom: 'var(--sp-2)' }}><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>Instagram</a></li>
            <li style={{ marginBottom: 'var(--sp-2)' }}><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>LinkedIn</a></li>
            <li><a href="#" style={{ color: 'rgba(255,255,255,0.8)', textDecoration: 'none', fontSize: '13px' }}>Newsletter</a></li>
          </ul>
        </div>
      </div>
      <div style={{
        borderTop: '1px solid rgba(255,255,255,0.1)',
        paddingTop: 'var(--sp-5)',
        textAlign: 'center',
        fontSize: '12px',
        color: 'rgba(255,255,255,0.6)',
      }}>
        <p style={{ margin: 0 }}>© 2024 WRYDECO. All rights reserved. Handcrafted with care.</p>
      </div>
    </footer>
  );
}
