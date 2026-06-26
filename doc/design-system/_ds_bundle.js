/* @ds-bundle: {"format":3,"namespace":"WRYDECODesignSystem_a05e31","components":[{"name":"Badge","sourcePath":"components/feedback/Badge.jsx"},{"name":"Button","sourcePath":"components/forms/Button.jsx"},{"name":"Input","sourcePath":"components/forms/Input.jsx"},{"name":"Divider","sourcePath":"components/layout/Divider.jsx"},{"name":"Card","sourcePath":"components/surfaces/Card.jsx"},{"name":"Footer","sourcePath":"ui_kits/website/Footer.jsx"},{"name":"Hero","sourcePath":"ui_kits/website/Hero.jsx"},{"name":"ProductDetail","sourcePath":"ui_kits/website/ProductDetail.jsx"},{"name":"ProductGallery","sourcePath":"ui_kits/website/ProductGallery.jsx"}],"sourceHashes":{"components/feedback/Badge.jsx":"d76496c2f1e3","components/forms/Button.jsx":"d444bd459053","components/forms/Input.jsx":"55ce090df83d","components/layout/Divider.jsx":"96db70103cef","components/surfaces/Card.jsx":"f8d28ad1abd6","ui_kits/website/Footer.jsx":"b5e00be29e25","ui_kits/website/Hero.jsx":"4e0af8624820","ui_kits/website/ProductDetail.jsx":"5cdd85e04bef","ui_kits/website/ProductGallery.jsx":"1d45b639ad54"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.WRYDECODesignSystem_a05e31 = window.WRYDECODesignSystem_a05e31 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/feedback/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Badge component - small label/tag
 */

function Badge({
  children,
  variant = 'default',
  size = 'md',
  style = {},
  className = '',
  ...props
}) {
  const baseStyles = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'var(--font-body)',
    fontWeight: 'var(--font-weight-semibold)',
    borderRadius: 'var(--radius-full)',
    whiteSpace: 'nowrap',
    textTransform: 'capitalize'
  };
  const sizeStyles = {
    sm: {
      padding: '4px 8px',
      fontSize: '11px'
    },
    md: {
      padding: '6px 12px',
      fontSize: '12px'
    },
    lg: {
      padding: '8px 16px',
      fontSize: '13px'
    }
  };
  const variantStyles = {
    default: {
      backgroundColor: 'var(--color-stone)',
      color: 'var(--text-primary)'
    },
    success: {
      backgroundColor: 'var(--color-sage)',
      color: 'white'
    },
    warning: {
      backgroundColor: 'var(--color-warning)',
      color: 'white'
    },
    error: {
      backgroundColor: 'var(--color-error)',
      color: 'white'
    },
    accent: {
      backgroundColor: 'var(--color-clay)',
      color: 'white'
    }
  };
  const finalStyle = {
    ...baseStyles,
    ...sizeStyles[size],
    ...variantStyles[variant],
    ...style
  };
  return /*#__PURE__*/React.createElement("span", _extends({
    className: className,
    style: finalStyle
  }, props), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Badge.jsx", error: String((e && e.message) || e) }); }

// components/forms/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Button component - primary action element
 * 
 * Usage:
 * ```jsx
 * <Button variant="primary" size="md" disabled={false}>
 *   Click me
 * </Button>
 * ```
 * 
 * Variants: primary, secondary, ghost
 * Sizes: sm, md, lg
 * 
 * @startingPoint section="UI Primitives" subtitle="Primary action button" viewport="300x60"
 */

function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  onClick,
  className = '',
  style = {},
  type = 'button',
  ...props
}) {
  const baseStyles = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'var(--font-body)',
    fontWeight: 'var(--font-weight-semibold)',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all var(--duration-short) var(--ease-standard)',
    outline: 'none'
  };
  const sizeStyles = {
    sm: {
      padding: '8px 16px',
      fontSize: '12px',
      minHeight: '32px'
    },
    md: {
      padding: '12px 20px',
      fontSize: '14px',
      minHeight: '40px'
    },
    lg: {
      padding: '16px 28px',
      fontSize: '16px',
      minHeight: '48px'
    }
  };
  const variantStyles = {
    primary: {
      backgroundColor: disabled ? 'var(--color-stone)' : 'var(--color-ebony)',
      color: disabled ? 'var(--color-linen)' : 'white'
    },
    secondary: {
      backgroundColor: disabled ? 'var(--color-stone)' : 'var(--color-stone)',
      color: disabled ? 'var(--color-linen)' : 'var(--color-ebony)'
    },
    ghost: {
      backgroundColor: 'transparent',
      color: disabled ? 'var(--color-linen)' : 'var(--color-ebony)',
      border: `1px solid ${disabled ? 'var(--color-stone)' : 'var(--color-linen)'}`
    }
  };
  const hoverStyles = !disabled && {
    primary: {
      backgroundColor: 'var(--color-bark)',
      boxShadow: 'var(--shadow-card-hover)'
    },
    secondary: {
      backgroundColor: 'var(--color-linen)'
    },
    ghost: {
      borderColor: 'var(--color-bark)',
      color: 'var(--color-bark)'
    }
  };
  const finalStyle = {
    ...baseStyles,
    ...sizeStyles[size],
    ...variantStyles[variant],
    ...style
  };
  return /*#__PURE__*/React.createElement("button", _extends({
    type: type,
    disabled: disabled,
    onClick: onClick,
    className: className,
    style: finalStyle,
    onMouseEnter: e => {
      if (!disabled && hoverStyles[variant]) {
        Object.assign(e.target.style, hoverStyles[variant]);
      }
    },
    onMouseLeave: e => {
      if (!disabled) {
        e.target.style.boxShadow = '';
        e.target.style.backgroundColor = variantStyles[variant].backgroundColor;
        e.target.style.borderColor = variantStyles[variant].borderColor || '';
        e.target.style.color = variantStyles[variant].color;
      }
    },
    onFocus: e => {
      e.target.style.outline = '2px solid var(--color-sage)';
      e.target.style.outlineOffset = '2px';
    },
    onBlur: e => {
      e.target.style.outline = 'none';
    }
  }, props), children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Button.jsx", error: String((e && e.message) || e) }); }

// components/forms/Input.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Input component - text input field
 */

function Input({
  type = 'text',
  placeholder = '',
  value = '',
  onChange = () => {},
  disabled = false,
  error = false,
  style = {},
  className = '',
  ...props
}) {
  const baseStyles = {
    fontFamily: 'var(--font-body)',
    fontSize: 'var(--font-size-body-md)',
    padding: 'var(--input-padding)',
    border: `1px solid ${error ? 'var(--color-error)' : 'var(--border-default)'}`,
    borderRadius: 'var(--radius-sm)',
    backgroundColor: disabled ? 'var(--bg-disabled)' : 'var(--bg-tertiary)',
    color: disabled ? 'var(--text-disabled)' : 'var(--text-primary)',
    cursor: disabled ? 'not-allowed' : 'text',
    transition: 'all var(--duration-short) var(--ease-standard)',
    minHeight: 'var(--input-height)',
    width: '100%',
    outline: 'none'
  };
  const finalStyle = {
    ...baseStyles,
    ...style
  };
  return /*#__PURE__*/React.createElement("input", _extends({
    type: type,
    placeholder: placeholder,
    value: value,
    onChange: onChange,
    disabled: disabled,
    className: className,
    style: finalStyle,
    onFocus: e => {
      e.target.style.borderColor = 'var(--color-sage)';
      e.target.style.boxShadow = 'var(--shadow-focus)';
    },
    onBlur: e => {
      e.target.style.borderColor = error ? 'var(--color-error)' : 'var(--border-default)';
      e.target.style.boxShadow = 'none';
    }
  }, props));
}
Object.assign(__ds_scope, { Input });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Input.jsx", error: String((e && e.message) || e) }); }

// components/layout/Divider.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Divider component - visual separator
 */

function Divider({
  orientation = 'horizontal',
  style = {},
  className = '',
  ...props
}) {
  const baseStyles = {
    backgroundColor: 'var(--border-light)'
  };
  const orientationStyles = {
    horizontal: {
      height: '1px',
      width: '100%'
    },
    vertical: {
      width: '1px',
      height: '100%'
    }
  };
  const finalStyle = {
    ...baseStyles,
    ...orientationStyles[orientation],
    ...style
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    className: className,
    style: finalStyle
  }, props));
}
Object.assign(__ds_scope, { Divider });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/layout/Divider.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Card.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Card component - elevated content container
 */

function Card({
  children,
  variant = 'default',
  elevation = 1,
  style = {},
  className = '',
  ...props
}) {
  const baseStyles = {
    backgroundColor: variant === 'elevated' ? 'white' : 'var(--color-cream)',
    borderRadius: 'var(--radius-sm)',
    padding: 'var(--card-padding)',
    transition: 'all var(--duration-short) var(--ease-standard)'
  };
  const elevationStyles = {
    1: {
      boxShadow: 'var(--shadow-elevation-1)'
    },
    2: {
      boxShadow: 'var(--shadow-elevation-2)'
    },
    3: {
      boxShadow: 'var(--shadow-elevation-3)'
    },
    4: {
      boxShadow: 'var(--shadow-elevation-4)'
    }
  };
  const finalStyle = {
    ...baseStyles,
    ...elevationStyles[elevation],
    ...style
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    className: className,
    style: finalStyle,
    onMouseEnter: e => {
      e.target.style.boxShadow = `var(--shadow-elevation-${Math.min(elevation + 1, 4)})`;
    },
    onMouseLeave: e => {
      e.target.style.boxShadow = elevationStyles[elevation].boxShadow;
    }
  }, props), children);
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Card.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Footer.jsx
try { (() => {
/**
 * Footer Section
 */
function Footer() {
  return /*#__PURE__*/React.createElement("footer", {
    style: {
      backgroundColor: 'var(--color-ebony)',
      color: 'white',
      padding: 'var(--sp-8) var(--layout-padding-desktop)',
      borderTop: '1px solid var(--border-dark)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: 'var(--sp-6)',
      marginBottom: 'var(--sp-8)',
      maxWidth: '1200px'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h4", {
    style: {
      fontSize: '14px',
      fontWeight: '600',
      marginBottom: 'var(--sp-3)'
    }
  }, "Shop"), /*#__PURE__*/React.createElement("ul", {
    style: {
      listStyle: 'none',
      padding: 0
    }
  }, /*#__PURE__*/React.createElement("li", {
    style: {
      marginBottom: 'var(--sp-2)'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "Furniture")), /*#__PURE__*/React.createElement("li", {
    style: {
      marginBottom: 'var(--sp-2)'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "Collections")), /*#__PURE__*/React.createElement("li", null, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "New Arrivals")))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h4", {
    style: {
      fontSize: '14px',
      fontWeight: '600',
      marginBottom: 'var(--sp-3)'
    }
  }, "About"), /*#__PURE__*/React.createElement("ul", {
    style: {
      listStyle: 'none',
      padding: 0
    }
  }, /*#__PURE__*/React.createElement("li", {
    style: {
      marginBottom: 'var(--sp-2)'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "Our Story")), /*#__PURE__*/React.createElement("li", {
    style: {
      marginBottom: 'var(--sp-2)'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "Sustainability")), /*#__PURE__*/React.createElement("li", null, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "Artisans")))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h4", {
    style: {
      fontSize: '14px',
      fontWeight: '600',
      marginBottom: 'var(--sp-3)'
    }
  }, "Support"), /*#__PURE__*/React.createElement("ul", {
    style: {
      listStyle: 'none',
      padding: 0
    }
  }, /*#__PURE__*/React.createElement("li", {
    style: {
      marginBottom: 'var(--sp-2)'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "Contact")), /*#__PURE__*/React.createElement("li", {
    style: {
      marginBottom: 'var(--sp-2)'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "Shipping")), /*#__PURE__*/React.createElement("li", null, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "Returns")))), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h4", {
    style: {
      fontSize: '14px',
      fontWeight: '600',
      marginBottom: 'var(--sp-3)'
    }
  }, "Connect"), /*#__PURE__*/React.createElement("ul", {
    style: {
      listStyle: 'none',
      padding: 0
    }
  }, /*#__PURE__*/React.createElement("li", {
    style: {
      marginBottom: 'var(--sp-2)'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "Instagram")), /*#__PURE__*/React.createElement("li", {
    style: {
      marginBottom: 'var(--sp-2)'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "LinkedIn")), /*#__PURE__*/React.createElement("li", null, /*#__PURE__*/React.createElement("a", {
    href: "#",
    style: {
      color: 'rgba(255,255,255,0.8)',
      textDecoration: 'none',
      fontSize: '13px'
    }
  }, "Newsletter"))))), /*#__PURE__*/React.createElement("div", {
    style: {
      borderTop: '1px solid rgba(255,255,255,0.1)',
      paddingTop: 'var(--sp-5)',
      textAlign: 'center',
      fontSize: '12px',
      color: 'rgba(255,255,255,0.6)'
    }
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0
    }
  }, "\xA9 2024 WRYDECO. All rights reserved. Handcrafted with care.")));
}
Object.assign(__ds_scope, { Footer });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Footer.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/Hero.jsx
try { (() => {
/**
 * Homepage Hero Section
 */
function Hero({
  onExplore = () => {}
}) {
  return /*#__PURE__*/React.createElement("section", {
    style: {
      paddingTop: 'var(--sp-8)',
      paddingBottom: 'var(--sp-8)',
      paddingLeft: 'var(--layout-padding-desktop)',
      paddingRight: 'var(--layout-padding-desktop)',
      textAlign: 'center',
      backgroundColor: 'var(--bg-primary)',
      borderBottom: '1px solid var(--border-light)'
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 'var(--font-size-display-lg)',
      marginBottom: 'var(--sp-4)',
      color: 'var(--text-primary)'
    }
  }, "Handcrafted Elegance"), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 'var(--font-size-body-lg)',
      color: 'var(--text-secondary)',
      maxWidth: '600px',
      marginLeft: 'auto',
      marginRight: 'auto',
      marginBottom: 'var(--sp-6)',
      lineHeight: 'var(--line-height-generous)'
    }
  }, "Discover our curated collection of premium artisan furniture and home d\xE9cor. Each piece is handcrafted with care and made from sustainably sourced materials."), /*#__PURE__*/React.createElement("button", {
    onClick: onExplore,
    style: {
      padding: '16px 28px',
      fontSize: '16px',
      fontWeight: '600',
      border: 'none',
      borderRadius: 'var(--radius-sm)',
      backgroundColor: 'var(--color-ebony)',
      color: 'white',
      cursor: 'pointer',
      transition: 'all var(--duration-short) var(--ease-standard)'
    },
    onMouseEnter: e => {
      e.target.style.backgroundColor = 'var(--color-bark)';
      e.target.style.boxShadow = 'var(--shadow-elevation-2)';
    },
    onMouseLeave: e => {
      e.target.style.backgroundColor = 'var(--color-ebony)';
      e.target.style.boxShadow = 'none';
    }
  }, "Explore Collection"));
}
Object.assign(__ds_scope, { Hero });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/Hero.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/ProductDetail.jsx
try { (() => {
/**
 * Product Detail View
 */
function ProductDetail() {
  const [quantity, setQuantity] = React.useState(1);
  const [showConsultation, setShowConsultation] = React.useState(false);
  return /*#__PURE__*/React.createElement("section", {
    style: {
      padding: 'var(--sp-8) var(--layout-padding-desktop)',
      backgroundColor: 'white'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: 'var(--sp-6)',
      maxWidth: '1200px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      backgroundColor: 'var(--bg-secondary)',
      borderRadius: 'var(--radius-sm)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '400px',
      fontSize: '120px'
    }
  }, "\uD83E\uDE91"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 'var(--sp-5)'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 'var(--font-size-display-md)',
      marginBottom: 'var(--sp-2)',
      color: 'var(--text-primary)'
    }
  }, "Walnut Shelving Unit"), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 'var(--font-size-body-lg)',
      color: 'var(--text-secondary)',
      marginBottom: 'var(--sp-3)'
    }
  }, "Premium handcrafted solid walnut with custom finishing"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 'var(--font-size-display-sm)',
      color: 'var(--color-clay)',
      fontWeight: '700',
      marginBottom: 'var(--sp-4)'
    }
  }, "$1,200")), /*#__PURE__*/React.createElement("div", {
    style: {
      borderTop: '1px solid var(--border-light)',
      borderBottom: '1px solid var(--border-light)',
      padding: 'var(--sp-4) 0'
    }
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: '12px',
      color: 'var(--text-tertiary)',
      textTransform: 'uppercase',
      marginBottom: 'var(--sp-2)',
      fontWeight: '600'
    }
  }, "Specifications"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: 'var(--sp-3)',
      fontSize: 'var(--font-size-body-sm)'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Dimensions:"), " 48\" W \xD7 72\" H \xD7 12\" D"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Material:"), " Solid Walnut"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Finish:"), " Natural Oil"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", null, "Weight:"), " 85 lbs"))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 'var(--sp-4)',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--sp-2)'
    }
  }, /*#__PURE__*/React.createElement("label", {
    style: {
      fontSize: '14px',
      fontWeight: '600'
    }
  }, "Qty:"), /*#__PURE__*/React.createElement("input", {
    type: "number",
    value: quantity,
    onChange: e => setQuantity(Math.max(1, parseInt(e.target.value) || 1)),
    style: {
      width: '60px',
      padding: '8px 12px',
      border: '1px solid var(--border-default)',
      borderRadius: 'var(--radius-sm)',
      fontSize: '14px'
    }
  })), /*#__PURE__*/React.createElement("button", {
    style: {
      flex: 1,
      padding: '14px 24px',
      backgroundColor: 'var(--color-ebony)',
      color: 'white',
      border: 'none',
      borderRadius: 'var(--radius-sm)',
      fontSize: '14px',
      fontWeight: '600',
      cursor: 'pointer',
      transition: 'all var(--duration-short) var(--ease-standard)'
    },
    onMouseEnter: e => {
      e.target.style.backgroundColor = 'var(--color-bark)';
      e.target.style.boxShadow = 'var(--shadow-elevation-2)';
    },
    onMouseLeave: e => {
      e.target.style.backgroundColor = 'var(--color-ebony)';
      e.target.style.boxShadow = 'none';
    }
  }, "Add to Cart")), /*#__PURE__*/React.createElement("button", {
    onClick: () => setShowConsultation(!showConsultation),
    style: {
      padding: '12px 20px',
      backgroundColor: 'transparent',
      color: 'var(--color-ebony)',
      border: '1px solid var(--color-linen)',
      borderRadius: 'var(--radius-sm)',
      fontSize: '14px',
      fontWeight: '600',
      cursor: 'pointer',
      transition: 'all var(--duration-short) var(--ease-standard)'
    },
    onMouseEnter: e => {
      e.target.style.borderColor = 'var(--color-bark)';
      e.target.style.color = 'var(--color-bark)';
    },
    onMouseLeave: e => {
      e.target.style.borderColor = 'var(--color-linen)';
      e.target.style.color = 'var(--color-ebony)';
    }
  }, "Schedule Private Consultation"), showConsultation && /*#__PURE__*/React.createElement("div", {
    style: {
      backgroundColor: 'var(--bg-primary)',
      padding: 'var(--sp-5)',
      borderRadius: 'var(--radius-sm)',
      border: '1px solid var(--border-light)'
    }
  }, /*#__PURE__*/React.createElement("h4", {
    style: {
      fontSize: '14px',
      fontWeight: '600',
      marginBottom: 'var(--sp-3)'
    }
  }, "Request Consultation"), /*#__PURE__*/React.createElement("input", {
    type: "email",
    placeholder: "Email",
    style: {
      width: '100%',
      padding: '10px 12px',
      marginBottom: 'var(--sp-2)',
      border: '1px solid var(--border-default)',
      borderRadius: 'var(--radius-sm)',
      fontSize: '14px'
    }
  }), /*#__PURE__*/React.createElement("button", {
    style: {
      width: '100%',
      padding: '10px',
      backgroundColor: 'var(--color-sage)',
      color: 'white',
      border: 'none',
      borderRadius: 'var(--radius-sm)',
      fontSize: '14px',
      fontWeight: '600',
      cursor: 'pointer'
    }
  }, "Submit")), /*#__PURE__*/React.createElement("div", {
    style: {
      backgroundColor: 'var(--bg-primary)',
      padding: 'var(--sp-4)',
      borderRadius: 'var(--radius-sm)',
      fontSize: 'var(--font-size-body-sm)',
      color: 'var(--text-secondary)'
    }
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      fontWeight: '600',
      marginBottom: 'var(--sp-2)'
    }
  }, "\u267B Sustainably Sourced"), /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0
    }
  }, "Crafted from responsibly harvested walnut. Each piece supports sustainable forestry practices.")))));
}
Object.assign(__ds_scope, { ProductDetail });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/ProductDetail.jsx", error: String((e && e.message) || e) }); }

// ui_kits/website/ProductGallery.jsx
try { (() => {
/**
 * Product Gallery Grid
 */
function ProductGallery() {
  const products = [{
    id: 1,
    name: 'Walnut Shelf',
    price: '$1,200',
    image: '🪑'
  }, {
    id: 2,
    name: 'Oak Bench',
    price: '$1,800',
    image: '🛋️'
  }, {
    id: 3,
    name: 'Maple Cabinet',
    price: '$2,400',
    image: '📦'
  }, {
    id: 4,
    name: 'Cherry Table',
    price: '$2,800',
    image: '📋'
  }];
  return /*#__PURE__*/React.createElement("section", {
    style: {
      padding: 'var(--sp-8) var(--layout-padding-desktop)',
      backgroundColor: 'white'
    }
  }, /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 'var(--font-size-display-md)',
      marginBottom: 'var(--sp-6)',
      color: 'var(--text-primary)'
    }
  }, "Featured Collection"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
      gap: 'var(--sp-5)'
    }
  }, products.map(product => /*#__PURE__*/React.createElement("div", {
    key: product.id,
    style: {
      backgroundColor: 'var(--color-cream)',
      borderRadius: 'var(--radius-sm)',
      overflow: 'hidden',
      boxShadow: 'var(--shadow-elevation-1)',
      cursor: 'pointer',
      transition: 'all var(--duration-short) var(--ease-standard)'
    },
    onMouseEnter: e => {
      e.currentTarget.style.boxShadow = 'var(--shadow-elevation-2)';
      e.currentTarget.style.transform = 'translateY(-2px)';
    },
    onMouseLeave: e => {
      e.currentTarget.style.boxShadow = 'var(--shadow-elevation-1)';
      e.currentTarget.style.transform = 'translateY(0)';
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '64px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      height: '200px',
      backgroundColor: 'var(--bg-secondary)'
    }
  }, product.image), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: 'var(--sp-5)'
    }
  }, /*#__PURE__*/React.createElement("h3", {
    style: {
      fontSize: 'var(--font-size-body-lg)',
      marginBottom: 'var(--sp-2)',
      color: 'var(--text-primary)'
    }
  }, product.name), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: 'var(--font-size-body-md)',
      color: 'var(--text-secondary)',
      marginBottom: 'var(--sp-3)'
    }
  }, product.price), /*#__PURE__*/React.createElement("button", {
    style: {
      width: '100%',
      padding: '12px 16px',
      border: '1px solid var(--color-linen)',
      backgroundColor: 'transparent',
      color: 'var(--text-primary)',
      borderRadius: 'var(--radius-sm)',
      cursor: 'pointer',
      fontSize: '14px',
      fontWeight: '600',
      transition: 'all var(--duration-short) var(--ease-standard)'
    },
    onMouseEnter: e => {
      e.target.style.borderColor = 'var(--color-bark)';
      e.target.style.color = 'var(--color-bark)';
    },
    onMouseLeave: e => {
      e.target.style.borderColor = 'var(--color-linen)';
      e.target.style.color = 'var(--text-primary)';
    }
  }, "View Details"))))));
}
Object.assign(__ds_scope, { ProductGallery });
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/website/ProductGallery.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Input = __ds_scope.Input;

__ds_ns.Divider = __ds_scope.Divider;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Footer = __ds_scope.Footer;

__ds_ns.Hero = __ds_scope.Hero;

__ds_ns.ProductDetail = __ds_scope.ProductDetail;

__ds_ns.ProductGallery = __ds_scope.ProductGallery;

})();
