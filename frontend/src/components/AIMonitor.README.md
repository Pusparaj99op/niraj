# AIMonitor Component - Styling Approach

## CSS Custom Properties for Dynamic Styling

This component uses CSS custom properties (CSS variables) to handle dynamic styling requirements while maintaining separation of concerns.

### Why This Approach?

The AIMonitor component displays data-driven visualizations (charts, progress bars, etc.) where heights and widths need to be calculated dynamically based on real-time data. The traditional approach would use inline `style` attributes, but we've refactored to use CSS custom properties for better maintainability.

### Implementation

1. **External CSS File** (`AIMonitor.css`):
   - Defines reusable CSS classes with CSS custom properties
   - Example: `.calibration-bar { height: var(--bar-height, 0); }`

2. **Component Usage**:
   - Sets dynamic values via CSS custom properties
   - Example: `style={{ '--bar-height': `${point.accuracy * 100}%` }}`

### Dynamic Elements

The following elements require dynamic styling based on real-time data:

1. **Calibration Curve Bars** (Line ~560)
   - Height calculated from accuracy percentage (0-100%)
   - CSS class: `.calibration-bar`

2. **Performance Accuracy Bars** (Line ~677)
   - Height based on model accuracy metrics
   - CSS class: `.performance-accuracy-bar`

3. **Performance P&L Bars** (Line ~683)
   - Height based on profit/loss values
   - CSS classes: `.performance-pnl-bar-positive`, `.performance-pnl-bar-negative`

4. **System Health Progress** (Line ~1509)
   - Width based on system resource usage
   - CSS class: `.system-health-progress`

### Linter Warnings

The linter may show warnings about inline styles on these elements. These warnings can be safely ignored because:

1. We're using CSS custom properties, not traditional inline styles
2. The values are truly dynamic and calculated from API data
3. This is the recommended modern approach for data-driven styling in React
4. All static styling has been properly extracted to the external CSS file

### Best Practices

- ✅ Static styles are in external CSS file
- ✅ Dynamic values use CSS custom properties
- ✅ TypeScript casting ensures type safety
- ✅ Semantic class names describe purpose
- ✅ Comments explain dynamic calculations

For more information on CSS custom properties, see:
https://developer.mozilla.org/en-US/docs/Web/CSS/Using_CSS_custom_properties
