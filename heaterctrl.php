<?php
    if ($_POST["cmd"] == "list") {
        header('Content-Type: application/json');
        system("./heaterctrl.py -b -o list -j");
    } elseif ($_POST["cmd"] == "remove") {
        header('Content-Type: application/json');
        system("./heaterctrl.py  -b -o remove -i " . $_POST["id"]);
        system("./heaterctrl.py -b -o list -j");
    } elseif ($_POST["cmd"] == "set") {
        header('Content-Type: application/json');
        system("./heaterctrl.py -b -o set -i " . $_POST["id"] . " -t " . $_POST["time"] . " -d " . $_POST["duration"]);
        system("./heaterctrl.py -b -o list -j");
    } elseif ($_POST["cmd"] == "on") {
        header('Content-Type: application/json');
        system("./heaterctrl.py -b -o on -i " . $_POST["id"]);
    } elseif ($_POST["cmd"] == "off") {
        header('Content-Type: application/json');
        system("./heaterctrl.py -b -o off -i " . $_POST["id"]);
    } elseif ($_POST["cmd"] == "test") {
        system($_POST["command"]);
    } else {
        header('Content-Type: application/json');
        $data = [ 'result' => 'FAIL', 'error' => "missing or unknown cmd '" . $_POST["id"] ."'"];
        echo json_encode( $data );
    }
?>