function toDate(f) {
    if (!f || f.length!=16) return null;
    var f = f.split(/-/);
    return new Date(f[0], f[1] - 1, f[2], f[3], f[4]);
}

var last = toDate(last_run);
var next = toDate(next_run);

if (last && next) {
    var now = new Date();
    var hours = Math.abs(now - last) / 36e5;
    if (hours > 1.5 && next < now) {
        var h = Math.round(hours);
        alert(
            "El script que genera esta página esta parado.\n"+
            "Los datos mostrados son de hace más de "+h+" hora"+(h==1?"":"s")+"."
        );
    }
}
