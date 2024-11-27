import ROOT
import numpy as np
import pyodbc
import os
import collections
import math

ROOT.gROOT.SetBatch(True)

def get_run_events():
    """Query database for run events"""
    connection_string = (
        'DRIVER={PostgreSQL};'
        'SERVER=sphnxdbmaster;'
        'DATABASE=intt;'
        'PORT=5432;'
    )
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT runnumber, nohitch, runtime, bco_stdev, bco_peak from intt_qa_expert;')
        return cursor.fetchall()

def get_num_events_from_daq(runnumbers):
    """Query database for number of events from daq"""
    connection_string = (
        'DRIVER={PostgreSQL};'
        'SERVER=sphnxdaqdbreplica;'
        'DATABASE=daq;'
        'PORT=5432;'
    )
    num_events = []
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()
        for runnumber in runnumbers:
            cursor.execute("SELECT eventsinrun FROM run WHERE runtype = 'physics' AND runnumber = ?", runnumber)
            row = cursor.fetchone()
            if row:
                num_events.append((runnumber, row[0]))
    return num_events

def process_run_file(hot_file_path):
    Dead, Cold, Hot = 0, 0, 0
    if os.path.isfile(hot_file_path):
        file_hot = ROOT.TFile.Open(hot_file_path)
        tree_hot = file_hot.Get("Multiple")
        if tree_hot:
            for i in range(tree_hot.GetEntries()):
                tree_hot.GetEvent(i)
                if tree_hot.Iflag == 1:
                    Dead += 1
                elif tree_hot.Iflag == 4:
                    Cold += 1
                elif tree_hot.Iflag == 8:
                    Hot += 1
        else:
            return None
    else:
        return None
    return [Dead, Cold, Hot]

def create_histograms():
    hist_nohitch = ROOT.TH1D("hist_nohitch", "Number of no hit channel", 50000, 0, 1000000)
    hist_nohitch_zoom = ROOT.TH1D("hist_nohitch_zoom", "Number of no hit channel", 100, 0, 30000)
    hist_runtime = ROOT.TH1D("hist_runtime", "Runtime", 66, 0, 65)
    hist_bco_stdev = ROOT.TH1D("hist_bco_stdev", "BCO peak StdDev", 100, 0, 100)
    hist_bco_peak = ROOT.TH1D("hist_bco_peak", "BCO peak position", 128, 0, 127)
    return hist_nohitch, hist_nohitch_zoom, hist_runtime, hist_bco_stdev, hist_bco_peak

def create_histograms_with_event_count():
    hist_nohitch = ROOT.TH1D("hist_nohitch_event_count", "Number of no hit channel with event count", 50000, 0, 1000000)
    hist_nohitch_zoom = ROOT.TH1D("hist_nohitch_zoom_event_count", "Number of no hit channel with event count", 100, 0, 30000)
    hist_runtime = ROOT.TH1D("hist_runtime_event_count", "Runtime with event count", 66, 0, 65)
    hist_bco_stdev = ROOT.TH1D("hist_bco_stdev_event_count", "BCO peak StdDev with event count", 100, 0, 100)
    hist_bco_peak = ROOT.TH1D("hist_bco_peak_event_count", "BCO peak position with event count", 128, 0, 127)
    return hist_nohitch, hist_nohitch_zoom, hist_runtime, hist_bco_stdev, hist_bco_peak

def create_canvas():
    canvas0 = ROOT.TCanvas("canvas_nohitch", "Number of no hit channel for all run", 800, 600)
    canvas00 = ROOT.TCanvas("canvas_nohitch_zoom", "Number of no hit channel for all run", 800, 600)
    canvas1 = ROOT.TCanvas("canvas_runtime", "Run time for all run", 800, 600)
    canvas2 = ROOT.TCanvas("canvas_bco_stdev", "BCO peak standard deviation for all run", 800, 600)
    canvas3 = ROOT.TCanvas("canvas_bco_peak", "BCO peak position for all run", 800, 600)
    return canvas0, canvas00, canvas1, canvas2, canvas3

def create_tree():
    tree = ROOT.TTree("tree", "tree")
    _runnum = np.ndarray(1, 'int')
    _runtime = np.ndarray(1, 'int')
    _nohitch = np.ndarray(1, 'int')
    _bco_stdev = np.ndarray(1, 'double')
    _bco_peak = np.ndarray(1, 'int')
    tree.Branch("runnumber", _runnum, "runnumber/I")
    tree.Branch("runtime", _runtime, "runtime/I")
    tree.Branch("nohitch", _nohitch, "nohitch/I")
    tree.Branch("bco_stdev", _bco_stdev, "bco_stdev/D")
    tree.Branch("bco_peak", _bco_peak, "bco_peak/I")
    return tree, _runnum, _runtime, _nohitch, _bco_stdev, _bco_peak

def fill_histograms_and_tree(rows, hist_nohitch, hist_nohitch_zoom, hist_runtime, hist_bco_stdev, hist_bco_peak, tree, _runnum, _runtime, _nohitch, _bco_stdev, _bco_peak):
    for i in range(6, len(rows)):
        runnum, nohitch, runtime, bco_stdev, bco_peak = rows[i]
        _runnum[0] = runnum
        _nohitch[0] = nohitch
        _runtime[0] = runtime
        _bco_peak[0] = bco_peak
        _bco_stdev[0] = bco_stdev
        hist_nohitch.Fill(nohitch, 1)
        hist_nohitch_zoom.Fill(nohitch, 1)
        hist_runtime.Fill(runtime, 1)
        hist_bco_stdev.Fill(bco_stdev, 1)
        hist_bco_peak.Fill(bco_peak, 1)
        tree.Fill()
        print(runnum, nohitch, runtime, bco_stdev, bco_peak)

def fill_histo_with_numevents(rows, num_events, hist_nohitch, hist_nohitch_zoom, hist_runtime, hist_bco_stdev, hist_bco_peak):
    event_count_dict = {runnumber: event_count for runnumber, event_count in num_events}
    for i in range(len(rows)):
        runnum, nohitch, runtime, bco_stdev, bco_peak = rows[i]
        event_count = event_count_dict.get(runnum, 1)
        hist_nohitch.Fill(nohitch, event_count)
        hist_nohitch_zoom.Fill(nohitch, event_count)
        hist_runtime.Fill(runtime, event_count)
        hist_bco_stdev.Fill(bco_stdev, event_count)
        hist_bco_peak.Fill(bco_peak, event_count)
        print(runnum, nohitch, runtime, bco_stdev, bco_peak, event_count)

def save_histograms_and_tree(hist_nohitch, hist_nohitch_zoom, hist_runtime, hist_bco_stdev, hist_bco_peak, tree):
    canvas0, canvas00, canvas1, canvas2, canvas3 = create_canvas()
    canvas0.cd()
    hist_nohitch.Draw()
    hist_nohitch.Write()
    canvas00.cd()
    hist_nohitch_zoom.Draw()
    hist_nohitch_zoom.Write()
    canvas1.cd()
    hist_runtime.Draw()
    hist_runtime.Write()
    canvas2.cd()
    hist_bco_stdev.Draw()
    hist_bco_stdev.Write()
    canvas3.cd()
    hist_bco_peak.Draw()
    hist_bco_peak.Write()
    tree.Write()

def main():
    sfile = ROOT.TFile("SaveFile.root", "RECREATE")
    rows = get_run_events()
    hist_nohitch, hist_nohitch_zoom, hist_runtime, hist_bco_stdev, hist_bco_peak = create_histograms()
    tree, _runnum, _runtime, _nohitch, _bco_stdev, _bco_peak = create_tree()
    fill_histograms_and_tree(rows, hist_nohitch, hist_nohitch_zoom, hist_runtime, hist_bco_stdev, hist_bco_peak, tree, _runnum, _runtime, _nohitch, _bco_stdev, _bco_peak)
    save_histograms_and_tree(hist_nohitch, hist_nohitch_zoom, hist_runtime, hist_bco_stdev, hist_bco_peak, tree)
    
    # Extract runnumbers from rows
    runnumbers = [row[0] for row in rows]
    
    # New histogram creation and filling with event count
    num_events = get_num_events_from_daq(runnumbers)
    hist_nohitch_event_count, hist_nohitch_zoom_event_count, hist_runtime_event_count, hist_bco_stdev_event_count, hist_bco_peak_event_count = create_histograms_with_event_count()
    fill_histo_with_numevents(rows, num_events, hist_nohitch_event_count, hist_nohitch_zoom_event_count, hist_runtime_event_count, hist_bco_stdev_event_count, hist_bco_peak_event_count)
    
    # Save new histograms
    hist_nohitch_event_count.Write()
    hist_nohitch_zoom_event_count.Write()
    hist_runtime_event_count.Write()
    hist_bco_stdev_event_count.Write()
    hist_bco_peak_event_count.Write()
    sfile.Close()

if __name__ == "__main__":
    main()