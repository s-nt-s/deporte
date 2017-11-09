var next = next_run.split(/-/);
next = new Date(next[0], next[1] - 1, next[2], next[3], next[4]);
if (next < new Date()) {
    alert('El script que genera esta página ha fallado, los datos pueden estar obsoletos');
}
