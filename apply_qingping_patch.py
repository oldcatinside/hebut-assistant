from pathlib import Path
p=Path("qingping-project/app/src/main/java/com/qingping/app/SkipAccessibilityService.java")
s=p.read_text()
s=s.replace("import java.util.Locale;", "import java.util.Locale;\nimport java.util.ArrayList;\nimport java.util.List;")
s=s.replace("    private static final int MAX_NODES = 320;", """    private static final int MAX_NODES = 500;
    private static final Pattern CLOSE = Pattern.compile("^(?:[×✕✖✗xX]|关闭|关闭弹窗|关闭广告|close|dismiss)$", Pattern.CASE_INSENSITIVE);
    private static final Pattern AD_MARKER = Pattern.compile("^(?:广告|广告[›>]?|ad|ads|advertisement|广告推广)$", Pattern.CASE_INSENSITIVE);""")
s=s.replace("        AccessibilityNodeInfo target = findSkipControl(root);", """        AccessibilityNodeInfo target = findSkipControl(root);
        boolean popupClose = false;
        if (target == null && StatsStore.isInAppEnabled(this)) {
            target = findAdPopupClose(root);
            popupClose = target != null;
        }""")
s=s.replace("        if (isGenericSkip(target)\n", "        if (!popupClose && isGenericSkip(target)\n")
idx=s.index("    private boolean matches(CharSequence text, CharSequence desc) {")
s=s[:idx]+'''    private AccessibilityNodeInfo findAdPopupClose(AccessibilityNodeInfo root) {
        List<AccessibilityNodeInfo> markers = new ArrayList<>();
        List<AccessibilityNodeInfo> closes = new ArrayList<>();
        ArrayDeque<AccessibilityNodeInfo> queue = new ArrayDeque<>();
        queue.add(root);
        int visited = 0;
        while (!queue.isEmpty() && visited++ < MAX_NODES) {
            AccessibilityNodeInfo n = queue.removeFirst();
            if (n.isVisibleToUser()) {
                if (matchesExact(n, AD_MARKER)) markers.add(n);
                if (matchesExact(n, CLOSE)) closes.add(n);
            }
            for (int i=0;i<n.getChildCount();i++) {
                AccessibilityNodeInfo child=n.getChild(i);
                if(child!=null) queue.addLast(child);
            }
        }
        if (markers.isEmpty() || closes.isEmpty()) return null;
        int w=getResources().getDisplayMetrics().widthPixels;
        int h=getResources().getDisplayMetrics().heightPixels;
        for (AccessibilityNodeInfo close : closes) {
            Rect cb=new Rect(); close.getBoundsInScreen(cb);
            if (cb.isEmpty() || cb.width()>w*.14 || cb.height()>h*.07) continue;
            if (cb.centerY()<h*.08 || cb.centerY()>h*.8) continue;
            for (AccessibilityNodeInfo marker : markers) {
                Rect mb=new Rect(); marker.getBoundsInScreen(mb);
                if (mb.isEmpty()) continue;
                if (Math.abs(cb.centerY()-mb.centerY())>h*.62) continue;
                if (Math.abs(cb.centerX()-mb.centerX())>w*.90) continue;
                if (mb.centerY()<=cb.centerY()+h*.08) continue;
                if (mb.centerY()>h*.88) continue;
                return close;
            }
        }
        return null;
    }

    private boolean matchesExact(AccessibilityNodeInfo node, Pattern pattern) {
        return matchesPattern(node.getText(), pattern) || matchesPattern(node.getContentDescription(), pattern);
    }

    private boolean matchesPattern(CharSequence raw, Pattern pattern) {
        if (raw==null) return false;
        String s=raw.toString().trim().replaceAll("\\\\s+", "");
        return s.length()>0 && s.length()<=24 && pattern.matcher(s).matches();
    }

'''+s[idx:]
p.write_text(s)
p=Path("qingping-project/app/build.gradle")
p.write_text(p.read_text().replace("versionCode 2","versionCode 3").replace("versionName '1.1.0'","versionName '1.2.0'"))
p=Path("qingping-project/app/src/main/java/com/qingping/app/MainActivity.java")
p.write_text(p.read_text().replace("也识别应用使用过程中的明确“跳过广告”按钮，误操作风险更高。","也尝试识别广告标识附近的弹窗关闭按钮与“跳过广告”控件，误操作风险更高。"))
