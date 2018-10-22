<?php
    header('Content-Type: application/json');
    if ($_POST["cmd"] == "list") {
        system("./heaterctrl.py -o list -j");
    } elseif ($_POST["cmd"] == "remove") {
        system("./heaterctrl.py -o remove -i " . $_POST["id"]);
        system("./heaterctrl.py -o list -j");
    } elseif ($_POST["cmd"] == "set") {
        system("./heaterctrl.py -o set -i " . $_POST["id"] . " -t " . $_POST["time"] . " -d " . $_POST["duration"]);
        system("./heaterctrl.py -o list -j");
    } elseif ($_POST["cmd"] == "on") {
        system("./heaterctrl.py -o on -i " . $_POST["id"]);
    } elseif ($_POST["cmd"] == "off") {
        system("./heaterctrl.py -o off -i " . $_POST["id"]);
    } else {
        $data = [ 'result' => 'FAIL', 'error' => "missing or unknown cmd '" . $_POST["id"] ."'"];
        echo json_encode( $data );
    }
?>